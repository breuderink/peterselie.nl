module.exports = (eleventyConfig) => {
  // Build inputs are first-class: content/ (pages) and files/ — media
  // (Git LFS) plus files/resources/ (stylesheet, banner, favicon).
  // Menu (content/_data/menu.json): an item with children stays open on its
  // own page and on its children's pages — the old site's expand behaviour,
  // now derived from the URL instead of per-page frontmatter.
  eleventyConfig.addFilter("inMenu", (item, url) =>
    item.url === url || (item.children || []).some((c) => c.url === url));
  eleventyConfig.addPassthroughCopy({ "files": "files" });
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
