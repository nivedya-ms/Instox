// Browser pHash — matches backend/services/vision_local.py byte-for-byte.
// 32x32 greyscale → DCT-II (orthonormal) → 8x8 low-freq → median split → 64 bits.
//
// Returns a hex string (16 chars) for easy transport / comparison. Callers who
// want to Hamming-compare can call `hammingHex(a, b)`.

(function () {
  const DCT_SIZE = 32;
  const HASH_SIZE = 8;

  // 1-D DCT-II with orthonormal normalization.
  function dct1d(vec) {
    const N = vec.length;
    const out = new Float64Array(N);
    const factor = Math.PI / (2 * N);
    for (let k = 0; k < N; k++) {
      let s = 0;
      for (let n = 0; n < N; n++) {
        s += vec[n] * Math.cos(factor * (2 * n + 1) * k);
      }
      out[k] = k === 0 ? s * Math.sqrt(1 / N) : s * Math.sqrt(2 / N);
    }
    return out;
  }

  function dct2d(matrix) {
    const N = matrix.length;
    const rowDcts = matrix.map(dct1d);
    const cols = [];
    for (let c = 0; c < N; c++) {
      const col = new Float64Array(N);
      for (let r = 0; r < N; r++) col[r] = rowDcts[r][c];
      cols.push(col);
    }
    const colDcts = cols.map(dct1d);
    const out = [];
    for (let r = 0; r < N; r++) {
      const row = new Float64Array(N);
      for (let c = 0; c < N; c++) row[c] = colDcts[c][r];
      out.push(row);
    }
    return out;
  }

  // Load an image blob/file into a 32x32 greyscale Float64Array via <canvas>.
  async function toGreyscale32(blob) {
    const url = URL.createObjectURL(blob);
    try {
      const img = new Image();
      img.decoding = 'async';
      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = url;
      });
      const canvas = document.createElement('canvas');
      canvas.width = DCT_SIZE;
      canvas.height = DCT_SIZE;
      const ctx = canvas.getContext('2d');
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'low';  // approximates PIL bilinear
      ctx.drawImage(img, 0, 0, DCT_SIZE, DCT_SIZE);
      const data = ctx.getImageData(0, 0, DCT_SIZE, DCT_SIZE).data;
      const matrix = [];
      for (let y = 0; y < DCT_SIZE; y++) {
        const row = new Float64Array(DCT_SIZE);
        for (let x = 0; x < DCT_SIZE; x++) {
          const i = (y * DCT_SIZE + x) * 4;
          // ITU-R 601 luma coefficients — same as PIL's "L" mode.
          const l = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
          row[x] = l;
        }
        matrix.push(row);
      }
      return matrix;
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  function medianExcludingDc(coeffs) {
    const nonDc = coeffs.slice(1);
    nonDc.sort((a, b) => a - b);
    const mid = Math.floor(nonDc.length / 2);
    return nonDc.length % 2 === 0 ? (nonDc[mid - 1] + nonDc[mid]) / 2 : nonDc[mid];
  }

  function bitsToHex(bits) {
    // bits is a length-64 array of 0/1, index 0 = most significant bit.
    let hex = '';
    for (let i = 0; i < 16; i++) {
      let nibble = 0;
      for (let j = 0; j < 4; j++) nibble = (nibble << 1) | bits[i * 4 + j];
      hex += nibble.toString(16);
    }
    return hex;
  }

  async function phash(blob) {
    const matrix = await toGreyscale32(blob);
    const dct = dct2d(matrix);
    const lowFreq = [];
    for (let y = 0; y < HASH_SIZE; y++) {
      for (let x = 0; x < HASH_SIZE; x++) lowFreq.push(dct[y][x]);
    }
    const median = medianExcludingDc(lowFreq);
    const bits = lowFreq.map((v) => (v > median ? 1 : 0));
    return bitsToHex(bits);
  }

  function popcount8(byte) {
    byte = byte - ((byte >> 1) & 0x55);
    byte = (byte & 0x33) + ((byte >> 2) & 0x33);
    return (byte + (byte >> 4)) & 0x0f;
  }

  function hammingHex(a, b) {
    if (a.length !== b.length) throw new Error('hash length mismatch');
    let dist = 0;
    for (let i = 0; i < a.length; i += 2) {
      const av = parseInt(a.substr(i, 2), 16);
      const bv = parseInt(b.substr(i, 2), 16);
      dist += popcount8(av ^ bv);
    }
    return dist;
  }

  function similarityHex(a, b) {
    return 1 - hammingHex(a, b) / 64;
  }

  window.InstoxPhash = { phash, hammingHex, similarityHex };
})();
