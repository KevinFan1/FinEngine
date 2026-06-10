import { findChecklistHeaderRow, validateChecklistHeaders } from "./common";

interface HeaderWorkerRequest {
    id: number;
    buffer: ArrayBuffer;
}

interface HeaderCheckResult {
    headerRowFound: boolean;
    valid: boolean;
    missing: string[];
    fileType: string;
    empty: boolean;
}

interface HeaderWorkerSuccess {
    id: number;
    ok: true;
    result: HeaderCheckResult;
}

interface HeaderWorkerFailure {
    id: number;
    ok: false;
    error: string;
}

type HeaderWorkerResponse = HeaderWorkerSuccess | HeaderWorkerFailure;

interface ZipEntry {
    name: string;
    method: number;
    compressedSize: number;
    localHeaderOffset: number;
}

const textDecoder = new TextDecoder("utf-8");

function getUint16(view: DataView, offset: number) {
    return view.getUint16(offset, true);
}

function getUint32(view: DataView, offset: number) {
    return view.getUint32(offset, true);
}

function findEndOfCentralDirectory(view: DataView) {
    const minOffset = Math.max(0, view.byteLength - 0xffff - 22);
    for (let offset = view.byteLength - 22; offset >= minOffset; offset -= 1) {
        if (getUint32(view, offset) === 0x06054b50) return offset;
    }
    throw new Error("无法读取 xlsx 文件结构");
}

function readZipEntries(buffer: ArrayBuffer) {
    const view = new DataView(buffer);
    const eocdOffset = findEndOfCentralDirectory(view);
    const entryCount = getUint16(view, eocdOffset + 10);
    let offset = getUint32(view, eocdOffset + 16);
    const entries = new Map<string, ZipEntry>();

    for (let index = 0; index < entryCount; index += 1) {
        if (getUint32(view, offset) !== 0x02014b50) break;
        const method = getUint16(view, offset + 10);
        const compressedSize = getUint32(view, offset + 20);
        const fileNameLength = getUint16(view, offset + 28);
        const extraLength = getUint16(view, offset + 30);
        const commentLength = getUint16(view, offset + 32);
        const localHeaderOffset = getUint32(view, offset + 42);
        const name = textDecoder.decode(new Uint8Array(buffer, offset + 46, fileNameLength));
        entries.set(name, { name, method, compressedSize, localHeaderOffset });
        offset += 46 + fileNameLength + extraLength + commentLength;
    }

    return entries;
}

function closedTagCount(text: string, tagName: string) {
    return text.match(new RegExp(`</${tagName}>`, "g"))?.length || 0;
}

async function readZipText(
    buffer: ArrayBuffer,
    entries: Map<string, ZipEntry>,
    name: string,
    shouldStop?: (text: string) => boolean,
) {
    const entry = entries.get(name);
    if (!entry) return "";
    const view = new DataView(buffer);
    const offset = entry.localHeaderOffset;
    if (getUint32(view, offset) !== 0x04034b50) throw new Error("xlsx 文件结构异常");
    const fileNameLength = getUint16(view, offset + 26);
    const extraLength = getUint16(view, offset + 28);
    const dataOffset = offset + 30 + fileNameLength + extraLength;
    const compressed = new Uint8Array(buffer, dataOffset, entry.compressedSize);
    let bytes: Uint8Array;

    if (entry.method === 0) {
        bytes = compressed;
    } else if (entry.method === 8) {
        return inflateRawText(compressed, shouldStop);
    } else {
        throw new Error("不支持的 xlsx 压缩格式");
    }

    const text = textDecoder.decode(bytes);
    return shouldStop ? stopAtUsefulPrefix(text, shouldStop) : text;
}

async function inflateRawText(bytes: Uint8Array, shouldStop?: (text: string) => boolean) {
    const DecompressionStreamCtor = (self as unknown as { DecompressionStream?: typeof DecompressionStream }).DecompressionStream;
    if (!DecompressionStreamCtor) throw new Error("当前浏览器不支持本地表头解析");
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStreamCtor("deflate-raw"));
    const reader = stream.getReader();
    const decoder = new TextDecoder("utf-8");
    let text = "";

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            text += decoder.decode(value, { stream: true });
            if (shouldStop?.(text)) {
                await reader.cancel().catch(() => undefined);
                break;
            }
        }
    } finally {
        reader.releaseLock();
    }

    text += decoder.decode();
    return shouldStop ? stopAtUsefulPrefix(text, shouldStop) : text;
}

function stopAtUsefulPrefix(text: string, shouldStop: (text: string) => boolean) {
    if (!shouldStop(text)) return text;
    return text;
}

function decodeXml(value: string) {
    return value
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&amp;/g, "&")
        .replace(/&quot;/g, '"')
        .replace(/&apos;/g, "'");
}

function cellRefToIndex(ref: string) {
    const letters = ref.match(/[A-Z]+/i)?.[0]?.toUpperCase();
    if (!letters) return -1;
    let index = 0;
    for (const char of letters) index = index * 26 + char.charCodeAt(0) - 64;
    return index - 1;
}

function resolveSheetTarget(target: string) {
    if (target.startsWith("/")) return target.slice(1);
    return `xl/${target.replace(/^\.\//, "")}`;
}

function resolveSheetPaths(workbookXml: string, relsXml: string) {
    const targets = new Map<string, string>();
    const relRegex = /<Relationship\b[^>]*>/g;
    let relMatch: RegExpExecArray | null;
    while ((relMatch = relRegex.exec(relsXml))) {
        const relation = relMatch[0];
        const id = relation.match(/\bId="([^"]+)"/)?.[1];
        const target = relation.match(/\bTarget="([^"]+)"/)?.[1];
        if (id && target) targets.set(id, resolveSheetTarget(target));
    }

    const paths: string[] = [];
    const sheetRegex = /<sheet\b[^>]*\br:id="([^"]+)"/g;
    let sheetMatch: RegExpExecArray | null;
    while ((sheetMatch = sheetRegex.exec(workbookXml))) {
        const path = targets.get(sheetMatch[1]);
        if (path) paths.push(path);
    }
    return paths.length ? paths : ["xl/worksheets/sheet1.xml"];
}

function parseNeededSharedStringIndexes(sheetXml: string) {
    const indexes = new Set<number>();
    const rows = firstRowsXml(sheetXml);
    for (const rowXml of rows) {
        const cellRegex = /<c\b([^>]*)>([\s\S]*?)<\/c>/g;
        let cellMatch: RegExpExecArray | null;
        while ((cellMatch = cellRegex.exec(rowXml))) {
            if (!/\bt="s"/.test(cellMatch[1])) continue;
            const value = cellMatch[2].match(/<v>([\s\S]*?)<\/v>/)?.[1];
            const index = Number(value);
            if (Number.isFinite(index)) indexes.add(index);
        }
    }
    return indexes;
}

function parseSharedStrings(sharedStringsXml: string, neededIndexes: Set<number>) {
    const strings = new Map<number, string>();
    if (!sharedStringsXml || neededIndexes.size === 0) return strings;
    const maxIndex = Math.max(...neededIndexes);
    const siRegex = /<si\b[^>]*>([\s\S]*?)<\/si>/g;
    let index = 0;
    let siMatch: RegExpExecArray | null;

    while ((siMatch = siRegex.exec(sharedStringsXml))) {
        if (neededIndexes.has(index)) {
            const textParts = Array.from(siMatch[1].matchAll(/<t\b[^>]*>([\s\S]*?)<\/t>/g)).map((match) => decodeXml(match[1]));
            strings.set(index, textParts.join(""));
        }
        if (index >= maxIndex && strings.size === neededIndexes.size) break;
        index += 1;
    }

    return strings;
}

function firstRowsXml(sheetXml: string) {
    const rows: string[] = [];
    const rowRegex = /<row\b[^>]*>[\s\S]*?<\/row>/g;
    let rowMatch: RegExpExecArray | null;
    while ((rowMatch = rowRegex.exec(sheetXml)) && rows.length < 5) {
        rows.push(rowMatch[0]);
    }
    return rows;
}

function cellValue(attrs: string, body: string, sharedStrings: Map<number, string>) {
    if (/\bt="s"/.test(attrs)) {
        const index = Number(body.match(/<v>([\s\S]*?)<\/v>/)?.[1]);
        return Number.isFinite(index) ? sharedStrings.get(index) || "" : "";
    }
    if (/\bt="inlineStr"/.test(attrs)) {
        return Array.from(body.matchAll(/<t\b[^>]*>([\s\S]*?)<\/t>/g)).map((match) => decodeXml(match[1])).join("");
    }
    return decodeXml(body.match(/<v>([\s\S]*?)<\/v>/)?.[1] || "");
}

function parseSheetRows(sheetXml: string, sharedStrings: Map<number, string>) {
    return firstRowsXml(sheetXml).map((rowXml) => {
        const row: string[] = [];
        const cellRegex = /<c\b([^>]*)>([\s\S]*?)<\/c>/g;
        let cellMatch: RegExpExecArray | null;
        let fallbackIndex = 0;
        while ((cellMatch = cellRegex.exec(rowXml))) {
            const attrs = cellMatch[1];
            const ref = attrs.match(/\br="([^"]+)"/)?.[1] || "";
            const index = cellRefToIndex(ref);
            row[index >= 0 ? index : fallbackIndex] = cellValue(attrs, cellMatch[2], sharedStrings);
            fallbackIndex += 1;
        }
        return row;
    });
}

function rowsAreEmpty(rows: string[][]) {
    return !rows.some((row) => row.some((value) => String(value || "").trim()));
}

function betterHeaderResult(current: HeaderCheckResult | null, candidate: HeaderCheckResult) {
    if (!current) return candidate;
    return candidate.missing.length < current.missing.length ? candidate : current;
}

async function buildHeaderResult(buffer: ArrayBuffer): Promise<HeaderCheckResult> {
    const entries = readZipEntries(buffer);
    const workbookXml = await readZipText(buffer, entries, "xl/workbook.xml");
    const relsXml = await readZipText(buffer, entries, "xl/_rels/workbook.xml.rels");
    const sheetXmls: string[] = [];
    const sharedStringIndexes = new Set<number>();

    for (const sheetPath of resolveSheetPaths(workbookXml, relsXml)) {
        const sheetXml = await readZipText(buffer, entries, sheetPath, (text) => closedTagCount(text, "row") >= 5);
        if (!sheetXml) continue;
        sheetXmls.push(sheetXml);
        for (const index of parseNeededSharedStringIndexes(sheetXml)) sharedStringIndexes.add(index);
    }
    if (!sheetXmls.length) {
        return { headerRowFound: false, valid: true, missing: [], fileType: "", empty: true };
    }
    const maxSharedStringIndex = sharedStringIndexes.size ? Math.max(...sharedStringIndexes) : -1;
    const sharedStringsXml =
        maxSharedStringIndex >= 0
            ? await readZipText(buffer, entries, "xl/sharedStrings.xml", (text) => closedTagCount(text, "si") > maxSharedStringIndex)
            : "";
    const sharedStrings = parseSharedStrings(sharedStringsXml, sharedStringIndexes);
    let best: HeaderCheckResult | null = null;
    let hasContent = false;

    for (const sheetXml of sheetXmls) {
        const rows = parseSheetRows(sheetXml, sharedStrings);
        if (rowsAreEmpty(rows)) continue;
        hasContent = true;
        const headerRow = findChecklistHeaderRow(rows);
        if (!headerRow) continue;
        const result = validateChecklistHeaders(headerRow.cells);
        const candidate = {
            headerRowFound: true,
            valid: result.valid,
            missing: result.missing,
            fileType: result.fileType,
            empty: false,
        };
        if (candidate.valid) return candidate;
        best = betterHeaderResult(best, candidate);
    }

    if (best) return best;
    if (!hasContent) return { headerRowFound: false, valid: true, missing: [], fileType: "", empty: true };
    return { headerRowFound: false, valid: false, missing: [], fileType: "", empty: false };
}

self.onmessage = async (event: MessageEvent<HeaderWorkerRequest>) => {
    const { id, buffer } = event.data;
    try {
        const response: HeaderWorkerResponse = {
            id,
            ok: true,
            result: await buildHeaderResult(buffer),
        };
        self.postMessage(response);
    } catch (error) {
        const response: HeaderWorkerResponse = {
            id,
            ok: false,
            error: error instanceof Error ? error.message : "表头检查失败",
        };
        self.postMessage(response);
    }
};

export {};
