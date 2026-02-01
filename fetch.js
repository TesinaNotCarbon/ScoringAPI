const url = args[0];
const apiResponse = await Functions.makeHttpRequest({
  url: url,
  method: "GET"
});
if (apiResponse.error) {
  throw Error("Fallo la llamada a la API");
}
const score = apiResponse.data.score;
return Functions.encodeUint256(score);