// Copies self-hosted third-party assets (Alpine.js, Inter font) from
// node_modules into app/static so the site has no runtime dependency on
// external CDNs. Run automatically after `npm install` and before `npm run build`.
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");

function copyFile(src, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
  console.log(`copied ${path.relative(ROOT, dest)}`);
}

// Alpine.js
copyFile(
  path.join(ROOT, "node_modules/alpinejs/dist/cdn.min.js"),
  path.join(ROOT, "app/static/vendor/alpinejs/alpine.min.js")
);

// Inter font (weights used by the design system)
const weights = [400, 500, 600, 700, 800];
for (const weight of weights) {
  copyFile(
    path.join(ROOT, `node_modules/@fontsource/inter/files/inter-latin-${weight}-normal.woff2`),
    path.join(ROOT, `app/static/fonts/inter/inter-latin-${weight}-normal.woff2`)
  );
}
