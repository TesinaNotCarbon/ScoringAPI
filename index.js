import express from "express";

const app = express();

/**
 * Health check (Render likes this)
 */
app.get("/", (req, res) => {
  res.send("Mock Score API is running");
});

/**
 * Mock score endpoint
 * Deterministic by default (good for Chainlink)
 */
app.get("/score", (req, res) => {
  res.json({
    score: 87
  });
});

/**
 * Optional: simulate failures (useful for testing)
 * /score?fail=true
 */
app.get("/score-unstable", (req, res) => {
  if (req.query.fail === "true") {
    return res.status(500).json({ error: "Simulated failure" });
  }

  res.json({ score: 87 });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Mock API listening on port ${PORT}`);
});
