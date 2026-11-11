# Tab Nap progress log
Done: extension code, jsc (245 pass), _locales from listing, check_release/package scripts, tests/e2e/harness.py (groups 1-12).
E2E so far (main phase): g1,g3,g4,g5 pass; g2 needed pendingUrl fix in by_url (applied, rerun pending).
Next: run g2,g6,g7 then links(8) evil(9) hostperm(10,11,12); write README.md; check_release; package.
Run: ONLY=2,6,7 python3 tests/e2e/harness.py (~1 min per phase; run in background, log to tests/e2e/run.log)
g2 wake fix (focus window in activate), g6 whitelist clobber fixed in options.js; rerun 2,6,7 then 8,9,10,11,12
g1-7 pass individually; running full harness -> tests/e2e/full.log
full run killed by restart at g3; now running ONLY=8,9 -> r89.log, then 10,11,12 -> r1012.log, then 1,3,4,5 -> r1345.log
g8,g9 PASS
FIXED bug: classify() rejected options page (sender.tab set) -> setProtection failed; rerun 10,11,12
g10 PASS
real DOM: ddg=textarea[name=q], wiki visible=input#ooui-php-1 (selectors updated); g11 thanks check adjusted; rerun 11,12
g10,g11,g12 PASS (real pages ddg/wiki/bing). Remaining: final regression of 1-7 after classify fix, then package
ALL DONE; only final report left
