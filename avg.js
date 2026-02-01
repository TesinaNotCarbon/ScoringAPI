const scores = args.map(s => parseInt(s));
const sum = scores.reduce((a, b) => a + b, 0);
const avg = Math.round(sum / scores.length);
return Functions.encodeUint256(avg);