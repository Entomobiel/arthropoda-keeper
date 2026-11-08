/*
 * Arthropoda Keeper – kleine QR-codegenerator (ISO/IEC 18004).
 *
 * Bytemodus, foutcorrectie M, versies 1–10 (tot 213 tekens): ruim genoeg
 * voor links zoals homeassistant://navigate/arthropoda?enclosure=KB-01.
 * Geen externe bibliotheken.
 */

// Codewoorden per versie (niveau M): [ec per blok, [[aantal blokken, datacodewoorden per blok], ...]]
const BLOCKS_M = [
  null,
  [10, [[1, 16]]],
  [16, [[1, 28]]],
  [26, [[1, 44]]],
  [18, [[2, 32]]],
  [24, [[2, 43]]],
  [16, [[4, 27]]],
  [18, [[4, 31]]],
  [22, [[2, 38], [2, 39]]],
  [22, [[3, 36], [2, 37]]],
  [26, [[4, 43], [1, 44]]],
];

const ALIGNMENT = [null, [], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34],
  [6, 22, 38], [6, 24, 42], [6, 26, 46], [6, 28, 50]];

// --- Galoisveld GF(256) en Reed-Solomon -------------------------------------

const EXP = new Uint8Array(512);
const LOG = new Uint8Array(256);
(() => {
  let x = 1;
  for (let i = 0; i < 255; i++) {
    EXP[i] = x;
    LOG[x] = i;
    x <<= 1;
    if (x & 0x100) x ^= 0x11d;
  }
  for (let i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
})();

const gfMul = (a, b) => (a === 0 || b === 0 ? 0 : EXP[LOG[a] + LOG[b]]);

function rsGenerator(degree) {
  let poly = [1];
  for (let i = 0; i < degree; i++) {
    const next = new Array(poly.length + 1).fill(0);
    for (let j = 0; j < poly.length; j++) {
      next[j] ^= poly[j];
      next[j + 1] ^= gfMul(poly[j], EXP[i]);
    }
    poly = next;
  }
  return poly;
}

function rsRemainder(data, degree) {
  const gen = rsGenerator(degree);
  const rem = new Array(degree).fill(0);
  for (const byte of data) {
    const factor = byte ^ rem.shift();
    rem.push(0);
    for (let i = 0; i < degree; i++) rem[i] ^= gfMul(gen[i + 1], factor);
  }
  return rem;
}

// --- Codewoorden -------------------------------------------------------------

function utf8(text) {
  return Array.from(new TextEncoder().encode(text));
}

function dataCapacity(version) {
  const [, groups] = BLOCKS_M[version];
  return groups.reduce((sum, [n, k]) => sum + n * k, 0);
}

function chooseVersion(length) {
  for (let v = 1; v <= 10; v++) {
    const countBits = v < 10 ? 8 : 16;
    if (4 + countBits + 8 * length <= 8 * dataCapacity(v)) return v;
  }
  throw new Error("Tekst te lang voor een QR-code (max. ongeveer 210 tekens).");
}

function codewords(bytes, version) {
  const capacity = dataCapacity(version);
  const bits = [];
  const put = (value, length) => { for (let i = length - 1; i >= 0; i--) bits.push((value >>> i) & 1); };
  put(0b0100, 4); // bytemodus
  put(bytes.length, version < 10 ? 8 : 16);
  for (const b of bytes) put(b, 8);
  put(0, Math.min(4, capacity * 8 - bits.length)); // terminator
  while (bits.length % 8) bits.push(0);
  const data = [];
  for (let i = 0; i < bits.length; i += 8) data.push(parseInt(bits.slice(i, i + 8).join(""), 2));
  for (let pad = 0xec; data.length < capacity; pad ^= 0xec ^ 0x11) data.push(pad);

  // Opdelen in blokken, foutcorrectie, afwisselend samenvoegen
  const [ecLength, groups] = BLOCKS_M[version];
  const blocks = [];
  let offset = 0;
  for (const [count, size] of groups) {
    for (let i = 0; i < count; i++) {
      const chunk = data.slice(offset, offset + size);
      offset += size;
      blocks.push({ data: chunk, ec: rsRemainder(chunk, ecLength) });
    }
  }
  const result = [];
  const maxData = Math.max(...blocks.map((b) => b.data.length));
  for (let i = 0; i < maxData; i++) for (const b of blocks) if (i < b.data.length) result.push(b.data[i]);
  for (let i = 0; i < ecLength; i++) for (const b of blocks) result.push(b.ec[i]);
  return result;
}

// --- Matrix -----------------------------------------------------------------

function bchFormat(mask) {
  const data = (0b00 << 3) | mask; // foutcorrectie M = 00
  let rem = data << 10;
  for (let i = 14; i >= 10; i--) if ((rem >>> i) & 1) rem ^= 0x537 << (i - 10);
  return ((data << 10) | rem) ^ 0x5412;
}

function bchVersion(version) {
  let rem = version << 12;
  for (let i = 17; i >= 12; i--) if ((rem >>> i) & 1) rem ^= 0x1f25 << (i - 12);
  return (version << 12) | rem;
}

const MASKS = [
  (r, c) => (r + c) % 2 === 0,
  (r) => r % 2 === 0,
  (r, c) => c % 3 === 0,
  (r, c) => (r + c) % 3 === 0,
  (r, c) => (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0,
  (r, c) => ((r * c) % 2) + ((r * c) % 3) === 0,
  (r, c) => (((r * c) % 2) + ((r * c) % 3)) % 2 === 0,
  (r, c) => (((r + c) % 2) + ((r * c) % 3)) % 2 === 0,
];

function baseMatrix(version) {
  const size = 17 + 4 * version;
  const m = Array.from({ length: size }, () => new Array(size).fill(null));
  const fn = Array.from({ length: size }, () => new Array(size).fill(false));
  const set = (r, c, v) => { m[r][c] = v; fn[r][c] = true; };

  const finder = (top, left) => {
    for (let r = -1; r <= 7; r++) for (let c = -1; c <= 7; c++) {
      const rr = top + r, cc = left + c;
      if (rr < 0 || cc < 0 || rr >= size || cc >= size) continue;
      const inside = r >= 0 && r <= 6 && c >= 0 && c <= 6;
      const dark = inside && (r === 0 || r === 6 || c === 0 || c === 6 || (r >= 2 && r <= 4 && c >= 2 && c <= 4));
      set(rr, cc, dark);
    }
  };
  finder(0, 0);
  finder(0, size - 7);
  finder(size - 7, 0);

  for (let i = 8; i < size - 8; i++) {
    set(6, i, i % 2 === 0);
    set(i, 6, i % 2 === 0);
  }

  const pos = ALIGNMENT[version];
  const last = pos.length - 1;
  pos.forEach((r, i) => pos.forEach((c, j) => {
    // Niet op de drie hoeken met een finder; wel over de timinglijnen heen.
    if ((i === 0 && j === 0) || (i === 0 && j === last) || (i === last && j === 0)) return;
    for (let dr = -2; dr <= 2; dr++) for (let dc = -2; dc <= 2; dc++) {
      set(r + dr, c + dc, Math.max(Math.abs(dr), Math.abs(dc)) !== 1);
    }
  }));

  // Formaatgebieden reserveren (worden later ingevuld) en de donkere module
  for (let i = 0; i < 9; i++) {
    if (!fn[8][i]) set(8, i, false);
    if (!fn[i][8]) set(i, 8, false);
  }
  for (let i = 0; i < 8; i++) {
    set(8, size - 1 - i, false);
    set(size - 1 - i, 8, false);
  }
  set(size - 8, 8, true);

  if (version >= 7) {
    const bits = bchVersion(version);
    for (let i = 0; i < 18; i++) {
      const bit = ((bits >>> i) & 1) === 1;
      const a = Math.floor(i / 3), b = (i % 3) + size - 11;
      set(a, b, bit);
      set(b, a, bit);
    }
  }
  return { m, fn, size };
}

function placeData(m, fn, size, cws) {
  const bits = [];
  for (const cw of cws) for (let i = 7; i >= 0; i--) bits.push((cw >>> i) & 1);
  let k = 0;
  let upward = true;
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right = 5;
    for (let n = 0; n < size; n++) {
      const row = upward ? size - 1 - n : n;
      for (let j = 0; j < 2; j++) {
        const col = right - j;
        if (fn[row][col]) continue;
        m[row][col] = k < bits.length ? bits[k] === 1 : false;
        k++;
      }
    }
    upward = !upward;
  }
}

function writeFormat(m, size, mask) {
  const bits = bchFormat(mask);
  const bit = (i) => ((bits >>> i) & 1) === 1;
  // Eerste kopie, rond de finder linksboven
  for (let i = 0; i <= 5; i++) m[i][8] = bit(i);
  m[7][8] = bit(6);
  m[8][8] = bit(7);
  m[8][7] = bit(8);
  for (let i = 9; i < 15; i++) m[8][14 - i] = bit(i);
  // Tweede kopie, verdeeld over rechtsboven en linksonder
  for (let i = 0; i < 8; i++) m[8][size - 1 - i] = bit(i);
  for (let i = 8; i < 15; i++) m[size - 15 + i][8] = bit(i);
  m[size - 8][8] = true; // donkere module
}

function penalty(m, size) {
  let score = 0;
  const lines = (get) => {
    for (let a = 0; a < size; a++) {
      let run = 1;
      for (let b = 1; b < size; b++) {
        if (get(a, b) === get(a, b - 1)) run++;
        else { if (run >= 5) score += run - 2; run = 1; }
      }
      if (run >= 5) score += run - 2;
      for (let b = 0; b + 10 < size; b++) {
        const seq = Array.from({ length: 11 }, (_, i) => get(a, b + i));
        const p1 = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0];
        const p2 = [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1];
        if (p1.every((v, i) => v === +seq[i]) || p2.every((v, i) => v === +seq[i])) score += 40;
      }
    }
  };
  lines((a, b) => m[a][b]);
  lines((a, b) => m[b][a]);
  for (let r = 0; r < size - 1; r++) for (let c = 0; c < size - 1; c++) {
    const v = m[r][c];
    if (v === m[r][c + 1] && v === m[r + 1][c] && v === m[r + 1][c + 1]) score += 3;
  }
  const dark = m.flat().filter(Boolean).length;
  score += Math.floor(Math.abs((dark * 20) / (size * size) - 10)) * 10;
  return score;
}

/** QR-matrix (true = donker). `mask` kan geforceerd worden (voor tests). */
export function qrMatrix(text, { mask = null, version = null } = {}) {
  const bytes = utf8(text);
  const v = version || chooseVersion(bytes.length);
  const cws = codewords(bytes, v);
  let best = null;
  for (const candidate of mask === null ? [0, 1, 2, 3, 4, 5, 6, 7] : [mask]) {
    const { m, fn, size } = baseMatrix(v);
    placeData(m, fn, size, cws);
    for (let r = 0; r < size; r++) for (let c = 0; c < size; c++) {
      if (!fn[r][c] && MASKS[candidate](r, c)) m[r][c] = !m[r][c];
    }
    writeFormat(m, size, candidate);
    const score = mask === null ? penalty(m, size) : 0;
    if (!best || score < best.score) best = { m, score, mask: candidate, version: v };
  }
  return best;
}

/** QR-code als SVG-tekst, met witrand (quiet zone) van 4 modules. */
export function qrSvg(text, { sizeMm = null } = {}) {
  const { m } = qrMatrix(text);
  const n = m.length;
  const total = n + 8;
  let path = "";
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) {
    if (m[r][c]) path += `M${c + 4},${r + 4}h1v1h-1z`;
  }
  const dim = sizeMm ? `width="${sizeMm}mm" height="${sizeMm}mm"` : "";
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${total} ${total}" ${dim} shape-rendering="crispEdges"><rect width="${total}" height="${total}" fill="#fff"/><path d="${path}" fill="#000"/></svg>`;
}
