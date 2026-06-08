import test from "node:test";
import assert from "node:assert/strict";
import { decodeCsvBuffer } from "./csvEncoding.ts";

test("decodeCsvBuffer decodes utf-8 csv exports", () => {
    const buffer = new TextEncoder().encode("店铺,金额\n旗舰店,12.3").buffer;

    assert.equal(decodeCsvBuffer(buffer), "店铺,金额\n旗舰店,12.3");
});

test("decodeCsvBuffer falls back to gb18030 csv exports", () => {
    const bytes = Uint8Array.from([
        0xb5, 0xea, 0xc6, 0xcc, 0x2c, 0xbd, 0xf0, 0xb6, 0xee, 0x0a, 0xc6,
        0xec, 0xbd, 0xa2, 0xb5, 0xea, 0x2c, 0x31, 0x32, 0x2e, 0x33,
    ]);

    assert.equal(
        decodeCsvBuffer(bytes.buffer),
        "店铺,金额\n旗舰店,12.3",
    );
});
