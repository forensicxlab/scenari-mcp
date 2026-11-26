# Third-party components

The MIT license covers this project's original MCP adapter, skill, documentation
and deployment examples. It does not relicense dependencies or grant rights to
Scenari/Dokiel names, logos, model packs, container images or course materials.

Python dependency versions and upstream locations are recorded in `uv.lock`.
They are installed separately and retain their own licenses. In particular,
`scenaripy-api` and `scsuitestarter-6-5` are upstream Scenari libraries; consult
their distributed license metadata before redistributing dependencies or a
combined binary distribution. The source ZIP contains no vendored libraries.

The Compose example downloads `scenari/suite-starter` from its publisher. The
image and separately installed Dokiel packs remain governed by their upstream
terms. They are not bundled in this repository or its release ZIPs.
The optional tar-compat image installs the distribution's `libarchive-tools`
package separately; that package retains its upstream licensing.

Private deployment pilots, branded Styler sources, native workspace exports,
screenshots and training evidence from development are excluded from the public
release. The optional Kasm block described by the skill requires a separately
provided compatible implementation.

This is an independent integration, not an official Scenari product.
