// Symlinks frontend/node_modules up to the repo root so that
// workload/frontend (a sibling of frontend/, not an ancestor of its
// node_modules) can resolve npm packages like "lucide-react" in its pages.
// Node/Rollup module resolution only walks up ANCESTOR directories from the
// importing file — this puts node_modules on that shared ancestor path.
//
// Uses a Windows junction (via the 'junction' type, ignored/treated as a
// plain symlink on POSIX) so this works without admin rights on Windows,
// during a Docker build, and in CI, via nothing more than `npm install`.
const fs = require("fs");
const path = require("path");

const target = path.resolve(__dirname, "..", "node_modules");
const linkPath = path.resolve(__dirname, "..", "..", "node_modules");

try {
  fs.symlinkSync(target, linkPath, "junction");
} catch (err) {
  if (err.code !== "EEXIST") {
    throw err;
  }
}
