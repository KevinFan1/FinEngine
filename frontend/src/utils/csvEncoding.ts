export function decodeCsvBuffer(buffer: ArrayBuffer): string {
    const encodings = ["utf-8", "gb18030"];
    for (const encoding of encodings) {
        try {
            return new TextDecoder(encoding, { fatal: true }).decode(buffer);
        } catch {
            // Try the next common CSV export encoding.
        }
    }
    return new TextDecoder("utf-8").decode(buffer);
}
