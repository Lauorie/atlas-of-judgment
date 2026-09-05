// List every string literal and template literal in a JS file, with offsets and
// enough syntactic context to decide which ones are display text.
//
//   NODE_PATH=<dir with acorn> node scripts/zh/js_literals.mjs file.js > literals.json
//
// Output: [{start, end, kind: "string"|"template", raw, value, ctx, exprs:[[s,e]...]}]
// where `ctx` is one of: key, compare, case, member, setlike, selector, attrname,
// setattr-style, style, fontish, value. Offsets are JS string indices (UTF-16),
// which equal Python str indices for this codebase (no astral characters).
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const acorn = require("acorn");
const walk = require("acorn-walk");

const src = readFileSync(process.argv[2], "utf8");
const ast = acorn.parse(src, { ecmaVersion: "latest", sourceType: "script", locations: false });

const SELECTOR_FNS = new Set(["querySelector", "querySelectorAll", "getElementById", "getElementsByClassName", "closest", "matches", "createElement", "createElementNS", "createTextNode"]);
const SETLIKE_FNS = new Set(["has", "includes", "add", "remove", "toggle", "contains", "indexOf", "startsWith", "endsWith", "split", "replace", "replaceAll", "test", "match", "getItem", "setItem", "removeItem", "addEventListener", "removeEventListener", "getAttribute", "removeAttribute", "hasAttribute", "getPropertyValue", "setProperty", "getContext", "toLocaleString", "toFixed", "padStart", "padEnd", "localeCompare", "assign", "open", "postMessage", "requestAnimationFrame", "RegExp", "matchMedia", "supports"]);
const TEXT_ATTRS = new Set(["aria-label", "title", "alt", "placeholder", "aria-description", "aria-valuetext", "data-tip", "data-label", "aria-roledescription"]);

function calleeName(node) {
  if (!node) return null;
  if (node.type === "Identifier") return node.name;
  if (node.type === "MemberExpression") return node.property && node.property.type === "Identifier" ? node.property.name : null;
  return null;
}

function classify(node, ancestors) {
  const parent = ancestors[ancestors.length - 2];
  const gp = ancestors[ancestors.length - 3];
  if (!parent) return "value";
  if (parent.type === "Property" && parent.key === node && !parent.computed) return "key";
  if (parent.type === "BinaryExpression" && ["===", "!==", "==", "!="].includes(parent.operator)) return "compare";
  if (parent.type === "SwitchCase" && parent.test === node) return "case";
  if (parent.type === "MemberExpression" && parent.property === node && parent.computed) return "member";
  if (parent.type === "ImportDeclaration" || parent.type === "ExpressionStatement") return "key";
  if (parent.type === "CallExpression" || parent.type === "NewExpression") {
    const fn = calleeName(parent.callee);
    if (fn === "setAttribute" || fn === "setAttributeNS") {
      const nameArg = parent.arguments[fn === "setAttribute" ? 0 : 1];
      if (node === nameArg) return "attrname";
      const attr = nameArg && nameArg.type === "Literal" ? String(nameArg.value) : null;
      return attr && TEXT_ATTRS.has(attr) ? "value" : "setattr-style";
    }
    if (fn && SELECTOR_FNS.has(fn)) return "selector";
    if (fn && SETLIKE_FNS.has(fn)) return "setlike";
    if (fn === "Set" || fn === "Map") return "setlike";
  }
  if (parent.type === "ArrayExpression" && gp && (gp.type === "NewExpression") && ["Set", "Map"].includes(calleeName(gp.callee))) return "setlike";
  if (parent.type === "AssignmentExpression" && parent.left.type === "MemberExpression") {
    const obj = parent.left.object;
    if (obj.type === "MemberExpression" && calleeName(obj) === "style") return "style";
    const prop = calleeName(parent.left);
    if (prop && ["className", "id", "href", "src", "type", "name", "value", "style", "cssText", "fill", "stroke", "transform", "d", "display"].includes(prop)) return "style";
  }
  if (parent.type === "Property" && parent.value === node) {
    const k = parent.key.type === "Identifier" ? parent.key.name : (parent.key.type === "Literal" ? String(parent.key.value) : "");
    if (/^(font-family|fontFamily|fill|stroke|color|background|font|transform|d|class|className|id|href|src|stroke-dasharray|text-anchor|dominant-baseline|filter|mask|clip-path|cursor|display|position|pointer-events|opacity|type|rel|target|style)$/.test(k)) return "fontish";
  }
  return "value";
}

// nearest enclosing `const NAME = ...` / `NAME = ...` and the property key the
// literal is a value of — used to admit single-word labels from label maps.
function owner(ancestors) {
  for (let i = ancestors.length - 2; i >= 0; i--) {
    const a = ancestors[i];
    if (a.type === "VariableDeclarator" && a.id.type === "Identifier") return a.id.name;
    if (a.type === "AssignmentExpression") return calleeName(a.left) || (a.left.type === "Identifier" ? a.left.name : null);
    if (a.type === "FunctionDeclaration" || a.type === "FunctionExpression" || a.type === "ArrowFunctionExpression") return null;
  }
  return null;
}
function propKey(ancestors) {
  const parent = ancestors[ancestors.length - 2];
  if (parent && parent.type === "Property" && parent.value === ancestors[ancestors.length - 1]) {
    return parent.key.type === "Identifier" ? parent.key.name : (parent.key.type === "Literal" ? String(parent.key.value) : null);
  }
  return null;
}

const out = [];
walk.fullAncestor(ast, (node, _state, ancestors) => {
  if (node.type === "Literal" && typeof node.value === "string") {
    out.push({ start: node.start, end: node.end, kind: "string", raw: src.slice(node.start, node.end), value: node.value,
      ctx: classify(node, ancestors), owner: owner(ancestors), key: propKey(ancestors), exprs: [] });
  } else if (node.type === "TemplateLiteral") {
    const parent = ancestors[ancestors.length - 2];
    if (parent && parent.type === "TaggedTemplateExpression") return;
    // cooked text with the `${...}` expressions kept verbatim
    let text = "";
    node.quasis.forEach((q, i) => {
      text += q.value.cooked;
      if (i < node.expressions.length) text += src.slice(q.end, node.quasis[i + 1].start);
    });
    out.push({ start: node.start, end: node.end, kind: "template", raw: src.slice(node.start, node.end),
      value: text, ctx: classify(node, ancestors), owner: owner(ancestors), key: propKey(ancestors),
      exprs: node.expressions.map(e => [e.start, e.end]) });
  }
});
out.sort((a, b) => a.start - b.start);
// non-computed string keys of object literals are never visited by the walker
// above; list them so data values that double as lookup keys can be protected.
const keys = new Set();
walk.full(ast, node => {
  if (node.type === "ObjectExpression") {
    for (const p of node.properties) {
      if (p.type === "Property" && !p.computed && p.key.type === "Literal" && typeof p.key.value === "string") keys.add(p.key.value);
    }
  }
});
process.stdout.write(JSON.stringify({ literals: out, keys: [...keys] }));
