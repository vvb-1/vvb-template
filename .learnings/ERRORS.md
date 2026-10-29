# Fel och förebyggande åtgärder

## 2026-10-29 — Omvänt filter hoppade över kodkontroller (#5)

Filtret `should_skip` matchade kod, men lint/test kördes endast när filtret
inte matchade. Därför hoppades kontrollerna över vid kodändringar.

Filtret och jobb-outputen heter nu `code`. Lint/test körs när outputen är
`true`. `.github/**`, `tests/**` och `test/**` omfattas uttryckligen.
Hemlighetsskanningen är fortfarande ovillkorlig. Gate-jobbet får endast
`contents: read` och `pull-requests: read`, vilket paths-filter behöver för
att läsa PR:ns ändrade filer. Inga skrivbehörigheter läggs till.

`python3 -m unittest discover -s tests -p test_ci_gate.py -v` kontrollerar workflowets filter,
outputkoppling och villkor för representativa kod-, test-, workflow- och
dokumentationsändringar. Det är lokala kontraktstester, inte en ersättning
för en riktig GitHub Actions-körning. Den ursprungliga inversionen ger
sju förväntade testfel. Ett separat test reproducerar saknad PR-läsbehörighet;
korrigeringarna ger sex godkända testmetoder. Ett sjunde test reproducerar
att manuell dispatch annars skulle hoppa över checks efter en docs-commit:
dispatch kör nu alltid lint/test och behöver ingen ändringsfiltrering.

Den tomma mallen har ingen npm-låsfil. Ovillkorlig `setup-node cache: npm`
skulle därför stoppa jobben före stackidentifieringen. Den optimeringen tas
bort och `package-manager-cache: false` hindrar automatisk npm-cache även
när genererade projekt anger npm utan låsfil. Installation och testkommandon
är oförändrade; ett åttonde kontrakttest skyddar detta mallkontrakt.

PR-granskningen hittade att obegränsad unittest-discovery även kunde köra
applikationstester före projektets beroendeinstallation. Gate-steget väljer
därför uttryckligen `test_ci_gate.py`. Ett nionde test kör workflowets faktiska
kommando i en syntetisk mall med en annan testmodul som kräver ännu
oinstallerade beroenden: utan filväljaren blir resultatet rött, med den grönt.

Separat kvarstående risk: befintliga Python-lint/teststeg sväljer fel med
`|| true`/fallback. De ändras inte inom denna avgränsade filterfix.
