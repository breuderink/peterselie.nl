module.exports = (eleventyConfig) => {
  // Output asset paths must stay byte-identical to the live site.
  // Assets live in the dated snapshot; restructure at deploy (t009).
  const A = "archive/live-2026-10-14";
  eleventyConfig.addPassthroughCopy({ [`${A}/files`]: "files" });
  eleventyConfig.addPassthroughCopy({ [`${A}/themes`]: "themes" });
  eleventyConfig.addPassthroughCopy({ [`${A}/misc`]: "misc" });
  // /modules/*.css were missed by the crawler (t001) and fetched 2026-10-14T08:25.
  eleventyConfig.addPassthroughCopy({ [`${A}/modules`]: "modules" });
  // Live Drupal URLs are extensionless (/contact, /tekoop); parity requires the same.
  eleventyConfig.configureErrorReporting({ allowMissingExtensions: true });
  return {
    templateFormats: ["html"],
    // Only content/ holds templates; archive/ and build/ must never be scanned.
    dir: { input: "content", includes: "../_includes", output: "build" },
  };
};
