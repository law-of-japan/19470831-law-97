# 労働省設置法の本移行の記録

作成日: 2026-11-25。試行（[試行結果](trial-result.md)、2026-11-19・11-24）の成果を、正本の`main`に移した記録。手順は作業ディレクトリの `labor-ministry-migration-plan.md`（本文データ・GitHubの変更前に作成）による。

## 決めたこと

| 論点 | 決定 |
|---|---|
| `main`の起点 | 親のないcommitから始めた。旧master `7d5d006` とは親子関係を持たないので、変更検査に旧履歴の境界を与えない |
| 旧ブランチ | 旧master `7d5d006ea805b2ebb7a6f9a0d24c7904b578befc`（`legacy.frozenAt`）と旧本文の `19470831_97` `125a1adb090b5548418cb243e71c56d951c3f51c` を凍結して残す。開いたままの旧PR #1 も残す |
| commit | 試行の5commit（訂正を含む）は再生せず、試行の先端 `4e294c3` の内容から作り直した（下の表） |
| 関連Record | 鉱山保安法 `19490516-law-70` と昭和二十四年法律第百六十二号 `ex0typ1a26` は、法令リポジトリを持たない`notCollected`のRecordとして登録台帳に登録する。関係（`amends`・`totallyRevises`）は本法の履歴マニフェストにある。試行の `docs/related/` は`main`に入れない |
| 未完了の照合 | 照合を待たずに収録する。`glyphCheck: unverified`、`correctionsSurveyed: unsurveyed` のまま |
| 検査器 | loj-validator `ba890a8`（仕様 `728b347`）に固定した |
| 附則で改正された他法 | 厚生省官制（附則第十四條）・労働基準法（附則第十五條）の改正の関係は記録しない（被改正法の側の作業） |

## commit

| commit | 種類 | 内容 |
|---|---|---|
| `38ab3d05e2b3a562ab13ec49639e77d3a24ddafb`（親なし） | `revisionAdd`（`wykk6n1d, grst9hg0`） | `history.yaml`・`rebuild.yaml`・`versions/`・`.gitattributes`・`docs/sources/` |
| `af64e5aeaf04ee479a581c834d4c24c7920ce8d6` | `auxiliary` | README・試行の記録・検証ワークフロー |
| 本記録のcommit | `auxiliary` | 本記録・`verify-migration.py`・`migration-validation/` |

- 正本のデータのファイル・`.gitattributes`・`docs/sources/`は、試行の先端と同じGitのオブジェクトである。本文は試行の結果から変えていない。
- 試行の記録・検証結果・READMEは正本のデータの外のファイルだけなので、`auxiliary`とした（CHG-01）。
- 検証ワークフローの`change-base`は、新しいブランチの最初のpush（ゼロのSHA）で空になるようにした。そのpushのCIは、L0・L1・L3・rebuildだけを実行する。

## 登録台帳

登録台帳の `records/labor-ministry-1947`（`e746351606b8015bf83b005b2703d89488a3c9a6`、`LoJ-Change: metadata`、親は台帳の`main` `125961a`）で3Recordを登録する。試行ブランチの記録との差は、本法の`location`（`github.com/law-of-japan/19470831-law-97`）・`canonicalBranch`（`main`）、関連2Recordの`repository`の削除、`fixed`を本法の最初のcommit `38ab3d0` に保存した画像のURLにしたことだけである。

## 検査

[verify-migration.py](verify-migration.py) で、本法の`main` `af64e5a` と台帳の `e746351` のcommit済みの木を検査した。結果は [migration-validation/](migration-validation/) にある。検査器は `ba890a8` のローカルビルド。

| 検査 | 結果 |
|---|---|
| 2版のL0・L1 | 合格（診断なし） |
| 本法のL3 historyStructure・evidence | 合格（診断なし） |
| rebuild | 合格（診断なし） |
| 台帳のregistry | 合格（診断なし） |
| 台帳と本法のL4（4区分） | 合格（診断なし） |
| 本法の変更検査（`--base`なし） | 合格（診断なし） |
| 台帳の変更検査（`--base 125961a`） | 合格（診断なし） |

不変条件（`invariants.json`）: 試行の先端とのデータの同一性、試行の先端との差の範囲、ファイルのモード（すべて`100644`）、2版の差が第六條第二号・第三号だけであること、画像のハッシュ、台帳の`fixed`のcommitとハッシュ、台帳の試行との差の範囲、旧ref・試行ブランチの不変。

形式検査の合格は、原典との一致や全履歴の網羅を示さない。

## 公開の手順（未実施）

1. 本法の`main`を新しいブランチとしてpushする。PRは作れない（旧masterと共通の祖先がない）。
2. CIの結果を確かめる。
3. 台帳の `records/labor-ministry-1947` をpushし、PRを作る。rebaseで取り込み、squash・merge commitは使わない。
4. 台帳のマージ後、確定したcommitで再検査し、本法の規定のブランチを`main`に切り替える。

## 残る作業

- 仮置きの字13か所の御署名原本での確認、官報正誤の調査、第四條第二号「の部」の官報の別の複製での確認。
- 厚生省官制・労働基準法の側への改正の関係の記録。
- 鉱山保安法・昭和二十四年法律第百六十二号の本文の収録（鉱山保安法は旧リポジトリからの移行になる）。
- 旧PR #1 の扱い。
