# xterm.js Vendor Files

These files are vendored copies of xterm.js and addons for terminal rendering.

## Sources

Downloaded on 2026-01-31 from npm via jsdelivr:

| File | Package | Version | Source URL |
|------|---------|---------|------------|
| xterm.min.css | @xterm/xterm | 5.5.0 | https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/css/xterm.min.css |
| xterm.min.js | @xterm/xterm | 5.5.0 | https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/lib/xterm.min.js |
| addon-fit.min.js | @xterm/addon-fit | 0.10.0 | https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.10.0/lib/addon-fit.min.js |
| addon-web-links.min.js | @xterm/addon-web-links | 0.11.0 | https://cdn.jsdelivr.net/npm/@xterm/addon-web-links@0.11.0/lib/addon-web-links.min.js |

## License

xterm.js is licensed under the MIT License.
https://github.com/xtermjs/xterm.js/blob/master/LICENSE

## Updating

To update these files, download new versions from jsdelivr and update this README:

```bash
cd server/static/xterm
curl -sL "https://cdn.jsdelivr.net/npm/@xterm/xterm@VERSION/css/xterm.min.css" -o xterm.min.css
curl -sL "https://cdn.jsdelivr.net/npm/@xterm/xterm@VERSION/lib/xterm.min.js" -o xterm.min.js
curl -sL "https://cdn.jsdelivr.net/npm/@xterm/addon-fit@VERSION/lib/addon-fit.min.js" -o addon-fit.min.js
curl -sL "https://cdn.jsdelivr.net/npm/@xterm/addon-web-links@VERSION/lib/addon-web-links.min.js" -o addon-web-links.min.js
```
