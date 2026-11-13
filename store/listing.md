# Chrome Web Store listing: Tab Nap (v1.0.0)

Everything below is meant to be checked against manifest.json, config.js, background.js, README.md, PRIVACY.md and docs/privacy.html before submitting. Character counts are stated next to each limited field. Copy only what is inside the code blocks.

---

## 1. Name and short description (shipped inside the package)

The store takes the item name (limit 75) and short summary (limit 132) from the package's `_locales/<locale>/messages.json` (`extName`, `extDescription`, referenced from manifest.json as `__MSG_extName__` and `__MSG_extDescription__`). Do NOT paste them in the dashboard. Exact strings and character counts:

| Locale | Name | Chars | Summary | Chars |
|---|---|---|---|---|
| en | Tab Nap – Tab Suspender & Memory Saver | 38 | Puts idle tabs to sleep with Chrome's own tab discarding. Frees memory, never loses a tab, and skips tabs with unsaved typing. | 126 |
| ro | Tab Nap – Suspendare file și economie de memorie | 48 | Adoarme filele inactive cu funcția nativă a Chrome. Eliberează memorie, nu pierzi nicio filă și ocolește filele cu text nesalvat. | 129 |
| de | Tab Nap – Tab-Suspender & Speicher sparen | 41 | Schickt inaktive Tabs mit Chromes Bordmitteln schlafen. Spart Speicher, verliert keinen Tab, schont Tabs mit ungespeichertem Text. | 130 |
| fr | Tab Nap – Suspension d'onglets et économie de mémoire | 53 | Endort les onglets inactifs via Chrome. Libère la mémoire, ne perd aucun onglet et épargne ceux dont la saisie est non enregistrée. | 131 |
| es | Tab Nap – Suspensor de pestañas y ahorro de memoria | 51 | Duerme las pestañas inactivas con la función nativa de Chrome. Libera memoria, no pierde ninguna y respeta las de texto sin guardar. | 132 |

## 2. Rules for the public descriptions

Do not name sites, brands or consent-platform vendors in any language's public description or summary. The Chrome Web Store flagged that as keyword spam for the sister extension Wait 24h (violation 'Yellow Argon', Nov 2026). Brand and site names are fine in the reviewer notes and permission justifications only. Tab Nap's public text contains none (checked by script: 0 brand names in every summary and description block).

## 3. Detailed description (EN)

```
Tab Nap is a tab suspender that puts idle tabs to sleep using Chrome's own tab discarding, so you get memory back without ever losing a tab. A sleeping tab keeps its place, title and address, and wakes up when you click it. Tab Nap never replaces a tab with a custom page.

HOW IT WORKS
• Idle tabs nap after 30 minutes by default (5, 15, 30, 60 or 120 in Options).
• Never napped: the tab you are looking at, pinned tabs (adjustable), tabs playing sound, tabs still loading, and sites on your whitelist.
• Optional "Protect tabs with unsaved typing": when you turn it on, Chrome asks for access to sites. Tab Nap then only learns a yes/no flag per tab that something was typed there, never what you typed (password fields are ignored entirely). It is off by default.
• Right-click a page: "Nap this tab now", "Never nap this site", "Nap all other tabs".
• Popup: tabs napping now, about how much memory that frees (an estimate based on an average you can adjust), lifetime tab-hours napped, and a list where you can wake any tab. Pause Tab Nap for an hour when you need to.
• Share: copy a short text about your napped tabs, with a link to the extension.

WHERE IT WORKS
Every tab Chrome allows to be discarded. Browser-internal pages are skipped quietly.

PRIVACY
• Everything stays on your device, in your browser's local extension storage.
• No ads, no tracking, no analytics, no accounts, and no network requests by the extension.
• Permissions: tabs, storage, alarms, contextMenus, scripting and favicon. No access to sites unless you turn on typing protection.

OPTIONAL SUPPORT
Tab Nap is free and built by one developer. If it helps, you can support it with a one-time payment (€3, €5, €10 or an amount you pick) through Stripe, or €2 a month. The ask appears in the popup only at milestones (100, 1,000 and 10,000 tab-hours napped), at most once per milestone and 30 days apart, never right after install. Choose "Don't ask again" and it stops for good. The same links are always in Options. Payments happen on Stripe's page; the extension never sees them.

The extension's interface is in English.

Open source: https://github.com/Overcrasher/tab-nap
```
Characters: 2161

---

## 4. Translations (paste per language in the dashboard)

### Detailed description (ro, Romanian)

```
Tab Nap este un suspendator de file care adoarme filele inactive folosind funcția nativă de „discard” din Chrome, astfel încât recuperezi memorie fără să pierzi vreodată o filă. O filă adormită își păstrează locul, titlul și adresa și se trezește când dai clic pe ea. Tab Nap nu înlocuiește niciodată o filă cu o pagină proprie.

CUM FUNCȚIONEAZĂ
• Filele inactive adorm după 30 de minute implicit (5, 15, 30, 60 sau 120 în Opțiuni).
• Nu adorm niciodată: fila la care te uiți, filele fixate (ajustabil), filele care redau sunet, filele încă în încărcare și site-urile din lista albă.
• Opțional „Protect tabs with unsaved typing”: când îl activezi, Chrome cere acces la site-uri. Tab Nap află apoi doar un semnal da/nu per filă că s-a tastat ceva acolo, niciodată ce ai tastat (câmpurile de parolă sunt ignorate complet). Este dezactivat implicit.
• Clic dreapta pe o pagină: „Nap this tab now”, „Never nap this site”, „Nap all other tabs”.
• Fereastra extensiei: filele adormite acum, cât de multă memorie eliberează aproximativ (o estimare pe baza unei medii ajustabile), orele-filă adormite în total și o listă din care poți trezi orice filă. Poți opri Tab Nap pentru o oră.
• Distribuire: copiezi un text scurt despre filele adormite, cu un link către extensie.

UNDE FUNCȚIONEAZĂ
Orice filă pe care Chrome o permite să fie adormită. Paginile interne ale browserului sunt ocolite discret.

CONFIDENȚIALITATE
• Totul rămâne pe dispozitivul tău, în spațiul local de stocare al extensiei.
• Fără reclame, fără urmărire, fără analiză, fără conturi și fără cereri de rețea din partea extensiei.
• Permisiuni: tabs, storage, alarms, contextMenus, scripting și favicon. Fără acces la site-uri decât dacă activezi protecția textului tastat.

SUSȚINERE OPȚIONALĂ
Tab Nap este gratuită și făcută de un singur dezvoltator. Dacă ți-a fost de folos, o poți susține printr-o plată unică (3 €, 5 €, 10 € sau o sumă aleasă de tine), prin Stripe sau 2 € pe lună. Propunerea apare în fereastra extensiei doar la praguri (100, 1.000 și 10.000 de ore-filă adormite), cel mult o dată pe prag, la minimum 30 de zile distanță, niciodată imediat după instalare. Cu „Don't ask again” se oprește definitiv. Aceleași linkuri sunt mereu în Opțiuni. Plata se face pe pagina Stripe; extensia nu o vede.

Interfața extensiei este în limba engleză.

Cod sursă deschis: https://github.com/Overcrasher/tab-nap
```
Characters: 2380

### Detailed description (de, German)

```
Tab Nap ist ein Tab-Suspender, der inaktive Tabs mit Chromes eigener Tab-Verwerfung schlafen schickt. So gewinnst du Speicher zurück, ohne je einen Tab zu verlieren. Ein schlafender Tab behält Platz, Titel und Adresse und wacht auf, sobald du ihn anklickst. Tab Nap ersetzt nie einen Tab durch eine eigene Seite.

SO FUNKTIONIERT ES
• Inaktive Tabs schlafen standardmäßig nach 30 Minuten ein (in den Optionen 5, 15, 30, 60 oder 120).
• Nie eingeschläfert werden: der Tab, den du ansiehst, angeheftete Tabs (einstellbar), Tabs mit Ton, noch ladende Tabs und Seiten auf deiner Whitelist.
• Optional „Protect tabs with unsaved typing“: Wenn du es einschaltest, fragt Chrome nach Zugriff auf Websites. Tab Nap erfährt dann nur ein Ja/Nein-Signal pro Tab, dass dort etwas getippt wurde, nie was du getippt hast (Passwortfelder werden komplett ignoriert). Standardmäßig aus.
• Rechtsklick auf eine Seite: „Nap this tab now“, „Never nap this site“, „Nap all other tabs“.
• Popup: aktuell schlafende Tabs, etwa wie viel Speicher das freigibt (eine Schätzung auf Basis eines einstellbaren Durchschnitts), insgesamt eingeschläferte Tab-Stunden und eine Liste, in der du jeden Tab wecken kannst. Pausiere Tab Nap bei Bedarf für eine Stunde.
• Teilen: Kopiere einen kurzen Text über deine schlafenden Tabs, mit einem Link zur Erweiterung.

WO ES FUNKTIONIERT
Jeder Tab, den Chrome verwerfen darf. Browserinterne Seiten werden still übersprungen.

DATENSCHUTZ
• Alles bleibt auf deinem Gerät, im lokalen Erweiterungsspeicher deines Browsers.
• Keine Werbung, kein Tracking, keine Analysen, keine Konten und keine Netzwerkanfragen der Erweiterung.
• Berechtigungen: tabs, storage, alarms, contextMenus, scripting und favicon. Kein Zugriff auf Websites, außer du schaltest den Schutz vor ungespeichertem Text ein.

FREIWILLIGE UNTERSTÜTZUNG
Tab Nap ist kostenlos und von einem einzelnen Entwickler gebaut. Wenn sie dir hilft, kannst du sie mit einer einmaligen Zahlung unterstützen (3 €, 5 €, 10 € oder ein Betrag deiner Wahl) über Stripe oder 2 € im Monat. Die Bitte erscheint im Popup nur bei Meilensteinen (100, 1.000 und 10.000 Tab-Stunden im Schlaf), höchstens einmal pro Meilenstein und mit mindestens 30 Tagen Abstand, nie direkt nach der Installation. Wähle „Don't ask again“, und sie hört für immer auf. Dieselben Links findest du immer in den Optionen. Die Zahlung läuft auf der Seite von Stripe; die Erweiterung sieht sie nie.

Die Oberfläche der Erweiterung ist auf Englisch.

Open Source: https://github.com/Overcrasher/tab-nap
```
Characters: 2525

### Detailed description (fr, French)

```
Tab Nap est un suspenseur d'onglets qui endort les onglets inactifs grâce à la fonction native de Chrome, pour libérer de la mémoire sans jamais perdre un onglet. Un onglet endormi garde sa place, son titre et son adresse, et se réveille d'un clic. Tab Nap ne remplace jamais un onglet par une page personnalisée.

COMMENT ÇA MARCHE
• Les onglets inactifs s'endorment après 30 minutes par défaut (5, 15, 30, 60 ou 120 dans les Options).
• Jamais endormis : l'onglet que vous regardez, les onglets épinglés (réglable), les onglets qui émettent du son, ceux en cours de chargement et les sites de votre liste blanche.
• Option « Protect tabs with unsaved typing » : une fois activée, Chrome demande l'accès aux sites. Tab Nap ne reçoit alors qu'un signal oui/non par onglet indiquant qu'on y a saisi quelque chose, jamais le contenu (les champs de mot de passe sont totalement ignorés). Désactivée par défaut.
• Clic droit sur une page : « Nap this tab now », « Never nap this site », « Nap all other tabs ».
• Fenêtre de l'extension : onglets endormis, mémoire libérée environ (estimation basée sur une moyenne réglable), heures-onglet cumulées et une liste pour réveiller n'importe quel onglet. Mettez Tab Nap en pause une heure si besoin.
• Partage : copiez un court texte sur vos onglets endormis, avec un lien vers l'extension.

OÙ ÇA FONCTIONNE
Tout onglet que Chrome autorise à mettre en veille. Les pages internes du navigateur sont ignorées discrètement.

CONFIDENTIALITÉ
• Tout reste sur votre appareil, dans le stockage local de l'extension de votre navigateur.
• Aucune publicité, aucun suivi, aucune analyse, aucun compte et aucune requête réseau de l'extension.
• Autorisations : tabs, storage, alarms, contextMenus, scripting et favicon. Aucun accès aux sites sauf si vous activez la protection de la saisie.

SOUTIEN FACULTATIF
Tab Nap est gratuite et conçue par un seul développeur. Si elle vous est utile, vous pouvez la soutenir par un paiement unique (3 €, 5 €, 10 € ou un montant de votre choix) via Stripe ou 2 € par mois. La demande n'apparaît dans la fenêtre de l'extension qu'à certains paliers (100, 1 000 et 10 000 heures-onglet en veille), au plus une fois par palier et à 30 jours d'intervalle, jamais juste après l'installation. Choisissez « Don't ask again » et elle s'arrête définitivement. Les mêmes liens sont toujours dans les Options. Le paiement se fait sur la page de Stripe ; l'extension ne le voit jamais.

L'interface de l'extension est en anglais.

Code source ouvert: https://github.com/Overcrasher/tab-nap
```
Characters: 2547

### Detailed description (es, Spanish)

```
Tab Nap es un suspensor de pestañas que duerme las pestañas inactivas con la función nativa de Chrome, así recuperas memoria sin perder nunca una pestaña. Una pestaña dormida conserva su lugar, título y dirección, y se despierta al hacer clic. Tab Nap nunca sustituye una pestaña por una página propia.

CÓMO FUNCIONA
• Las pestañas inactivas se duermen tras 30 minutos por defecto (5, 15, 30, 60 o 120 en Opciones).
• Nunca se duermen: la pestaña que estás viendo, las fijadas (ajustable), las que reproducen sonido, las que aún cargan y los sitios de tu lista blanca.
• Opción «Protect tabs with unsaved typing»: al activarla, Chrome pide acceso a los sitios. Tab Nap solo recibe entonces un aviso sí/no por pestaña de que se escribió algo, nunca lo que escribiste (los campos de contraseña se ignoran por completo). Desactivada por defecto.
• Clic derecho en una página: «Nap this tab now», «Never nap this site», «Nap all other tabs».
• Ventana de la extensión: pestañas dormidas ahora, cuánta memoria libera aproximadamente (estimación según una media ajustable), horas-pestaña acumuladas y una lista para despertar cualquier pestaña. Pausa Tab Nap una hora si lo necesitas.
• Compartir: copia un texto breve sobre tus pestañas dormidas, con un enlace a la extensión.

DÓNDE FUNCIONA
Cualquier pestaña que Chrome permita descartar. Las páginas internas del navegador se omiten en silencio.

PRIVACIDAD
• Todo se queda en tu dispositivo, en el almacenamiento local de extensiones de tu navegador.
• Sin anuncios, sin seguimiento, sin analítica, sin cuentas y sin solicitudes de red por parte de la extensión.
• Permisos: tabs, storage, alarms, contextMenus, scripting y favicon. Sin acceso a sitios salvo que actives la protección del texto sin guardar.

APOYO OPCIONAL
Tab Nap es gratuita y la ha creado un solo desarrollador. Si te resulta útil, puedes apoyarla con un pago único (3 €, 5 €, 10 € o un importe a tu elección) a través de Stripe o 2 € al mes. La petición aparece en la ventana de la extensión solo en ciertos hitos (100, 1.000 y 10.000 horas-pestaña dormidas), como máximo una vez por hito y con 30 días de separación, nunca justo después de instalar. Elige «Don't ask again» y se detiene para siempre. Los mismos enlaces están siempre en Opciones. El pago se hace en la página de Stripe; la extensión nunca lo ve.

La interfaz de la extensión está en inglés.

Código abierto: https://github.com/Overcrasher/tab-nap
```
Characters: 2435

---

## 5. Category and language

- Category: Productivity › Tools.
- Languages: English (default); Romanian (ro), German (de), French (fr) and Spanish (es) as added localized listings.

## 6. Single purpose statement (Privacy practices tab)

```
Tab Nap has one purpose: to free memory by putting idle browser tabs to sleep using Chrome's own tab discarding, without ever closing a tab or changing its address, and to protect tabs with unsaved typing and other tabs that should stay awake.
```

## 7. Permission justifications

### tabs
```
Needed to list tabs, read their last-activity state, title and address (for the popup list and the whitelist), and to call chrome.tabs.discard() on idle tabs. Tab Nap only discards; it never changes a tab's URL.
```

### storage
```
Stores settings, the whitelist, lifetime counters and donation state in chrome.storage.local, and short-lived working state (last activity per tab, tabs napped by Tab Nap, a yes/no "has unsaved typing" flag per tab) in chrome.storage.session. Nothing is transmitted.
```

### alarms
```
A once-a-minute alarm checks which tabs have been idle longer than the threshold and updates the tab-hours counter, even when the service worker was stopped.
```

### contextMenus
```
Adds three right-click items: "Nap this tab now", "Never nap this site" and "Nap all other tabs".
```

### scripting
```
Used only with chrome.scripting.registerContentScripts, after the user turns on "Protect tabs with unsaved typing" and grants the optional access, to register a small script that reports a yes/no flag when a field in the page was edited. The script never sends field contents and ignores password fields.
```

### favicon
```
Lets the popup show each napped tab's icon through the extension's own _favicon URL, instead of loading images from the internet.
```

### Optional host permissions (<all_urls>)
```
Requested only if the user turns on "Protect tabs with unsaved typing". Without it, Tab Nap has no access to any site and still works (it discards idle tabs, but cannot see unsaved form input). Revocable from the options page or chrome://extensions.
```

### Are you using remote code?
Answer: **No**
```
No. All JavaScript is bundled in the extension package. It does not load or evaluate remote scripts, remote modules or WebAssembly, uses no eval, and its extension-page CSP is script-src 'self'. It makes no network requests of its own.
```

## 8. Data usage disclosures (Privacy practices tab)

Recommended answers. CWS defines "collect" as data transmitted off the user's device or handled by the developer. Tab Nap never transmits anything and has no server, so strictly nothing is collected. Recommended checkbox: tick **User activity (a yes/no flag that something was typed in a tab, only if the user turns the optional protection on)**. Leave every other box unticked (the extension never sees payment details; Stripe handles them on its own page).

Tab titles and addresses are read only to build the popup list and match the whitelist, and stay on the device. Keep Website content and Web history unticked; if a reviewer asks for it, explain that no page content is read and nothing is transmitted.

Certifications (tick all three):
- I do not sell or transfer user data to third parties, outside of the approved use cases.
- I do not use or transfer user data for purposes that are unrelated to my item's single purpose.
- I do not use or transfer user data to determine creditworthiness or for lending purposes.

## 9. URLs

- Privacy policy URL: https://overcrasher.github.io/tab-nap/privacy.html
- Homepage URL: https://overcrasher.github.io/tab-nap/
- Support URL: https://github.com/Overcrasher/tab-nap/issues

## 10. Screenshots, promo tiles and icon (upload order)

The Chrome Web Store has no per-screenshot caption field. Upload in this order from store/images/ (headline is printed on each image):

1. screenshot-1-popup.png: "Idle tabs nap. Memory comes back." / the popup with 7 napping tabs, the estimated memory saved and the sleeping-tab list
2. screenshot-2-sleeping-tabs.png: "Chrome's own tab sleeping. No tabs lost." / a browser window (drawn) with awake and greyed asleep tabs and the real popup
3. screenshot-3-protection.png: "Never naps a tab you were typing in." / the Options page: threshold, never-nap sites, unsaved typing protection (switch shown on), memory, pause
4. screenshot-4-menu.png: "Nap a tab right now, or never nap a site." / the right-click menu with "Nap this tab now", "Never nap this site", "Nap all other tabs" (drawn illustration)
5. screenshot-5-privacy.png: "No accounts. No tracking. Nothing leaves your browser." / popup header and counters beside three privacy points

Promo tiles: promo-small-440x280.png and promo-marquee-1400x560.png: icon, name, "Tab suspender & memory saver" and "Idle tabs sleep. Nothing is lost."

Store icon: store-icon-128.png (96px artwork centred on a transparent 128px canvas, from icons/icon128.png).

All images are generated by tools/store_images.py (real UI captured from the unpacked extension; pages are invented fixtures, no third-party names or logos).

## 11. Notes for the reviewer

```
Tab Nap puts idle tabs to sleep using Chrome's own chrome.tabs.discard(). It never rewrites a tab's URL. No account or login is needed, and nothing is sent anywhere.

Quick test (about 3 minutes):
1. Load the extension and pin it. Open 3 or 4 ordinary https tabs.
2. Right-click any page, choose "Nap this tab now": the tab is discarded (grey/faded in the tab strip); clicking it reloads the same URL. Menu items "Never nap this site" and "Nap all other tabs" are also there. The active tab is never napped.
3. Open the toolbar popup: "Currently napping: N tabs, ≈ X GB (estimated)", the lifetime tab-hours, and the list of napped tabs with their icons. Click a tab in the list to wake it.
4. Options: idle threshold (5/15/30/60/120 min; default 30), pinned/audible protection, average MB per tab, whitelist, pause, and the switch "Protect tabs with unsaved typing". Turning the switch on shows Chrome's permission prompt (optional_host_permissions <all_urls>); it is off by default, so a fresh install requests no site access. When on, a tab where text was typed in a field is skipped by the idle check (only a yes/no flag is stored, never contents).
5. The idle check runs once a minute (alarm). To see it quickly, set the threshold to 5 minutes and leave a tab in the background.

Optional support: free extension. The support banner appears in the popup only at 100, 1,000 and 10,000 tab-hours napped, at most once per milestone, 30 days apart. The same Stripe links (and a small "support monthly" link) are always in Options. Payments happen on Stripe's page.

Permissions: tabs, storage, alarms, contextMenus, scripting, favicon; optional access to all sites only for the typing protection. No remote code, no network requests by the extension. Source: https://github.com/Overcrasher/tab-nap
```

## 12. Pre-submission checklist

- [ ] Run `python3 tools/check_release.py --release` and confirm it exits 0 (Stripe links valid and non-test, THANKS_URL matches the manifest, locale limits).
- [ ] Run the unit tests (see README) and load the unpacked folder one last time on real pages.
- [ ] Run `python3 tools/package.py`, which runs the release check and writes dist/tab-nap-<version>.zip; upload that zip.
- [ ] Confirm the manifest version is correct (1.0.0 for the first upload; bump for every later upload).
- [ ] Register a Chrome Web Store developer account (one-time US$5 fee) and verify the contact email; set the publisher name to Quantumbyte Labs.
- [ ] Confirm GitHub Pages is live: https://overcrasher.github.io/tab-nap/, privacy.html and thanks.html all open.
- [ ] Create the 5 screenshots (1280x800) matching section 10, plus the small promo tile (440x280); the marquee tile (1400x560) is optional.
- [ ] Paste the detailed description in each language (EN, RO, DE, FR, ES; name and short summary come from the package), category, single purpose, permission justifications, data disclosures and reviewer notes.
- [ ] Tick the three certification statements and set remote code to No.
- [ ] After publishing: put the real store URL into docs/index.html (the TODO(store-url) block), the README and the siblings' "More from the same developer" lists.
- [ ] Set visibility (Public) and distribution regions, then submit for review.
