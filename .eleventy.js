module.exports = (eleventyConfig) => {
  // Output asset paths must stay byte-identical to the live site.
  // Build inputs are first-class (files/, themes/, misc/); the dated
  // snapshot is the validator's oracle and re-import source only. (The
  // 2.0 build links one stylesheet, themes/peterselie/style.css; the old
  // modules/*.css are served to the oracle via its own symlink.)
  // Menu (content/_data/menu.json): an item with children stays open on its
  // own page and on its children's pages — the old site's expand behaviour,
  // now derived from the URL instead of per-page frontmatter.
  eleventyConfig.addFilter("inMenu", (item, url) =>
    item.url === url || (item.children || []).some((c) => c.url === url));
  eleventyConfig.addPassthroughCopy({ "files": "files" });
  eleventyConfig.addPassthroughCopy({ "themes": "themes" });
  eleventyConfig.addPassthroughCopy({ "misc": "misc" });
  // Pages emit /slug/ directories (build/slug/index.html): GitHub Pages
  // infers Content-Type from the file extension and cannot serve an
  // extensionless page as HTML. Old extensionless URLs (/contact) keep
  // resolving via Pages' 301 redirect to /contact/ (verify first deploy,
  // DEPLOY.md).
  // Live URLs contain raw spaces; emit link hrefs verbatim (no %20).
  eleventyConfig.amendLibrary("md", (md) => {
    md.normalizeLink = (link) => link;
    // GFM line breaks: a single newline inside a paragraph renders as <br>,
    // so content files read line-by-line (no <br> tags in the common case).
    md.set({ breaks: true });
  });
  return {
    templateFormats: ["html", "md"],
    dir: { input: "content", includes: "../_includes", output: "build" },
  };
};
