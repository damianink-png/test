//! A standalone HTML BOM from the already generated and escaped report tables.
pub fn bom_document(source: &str, role: usize) -> Result<String, String> {
    if role > 1 { return Err("Nieprawidłowy BOM".into()); }
    let marker = "<details class=\"panel bom-panel\">";
    let section = source.split(marker).nth(role + 1).ok_or("Brak BOM w tym raporcie. Włącz zestawienie BOM i wykonaj nowe porównanie.")?;
    let end = section.find("</details>").ok_or("Niekompletny BOM w raporcie")?;
    let content = &section[..end];
    let letter = if role == 0 { "A" } else { "B" };
    Ok(format!(r#"<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BOM {letter} — DS Compare</title><style>body{{font:14px 'Segoe UI',sans-serif;margin:24px;color:#18283a;background:#f8fafc}}details{{background:white;border:1px solid #d7e0e8;border-radius:8px;padding:16px}}summary{{font-size:18px;font-weight:600;margin-bottom:18px}}input{{padding:10px;width:min(480px,90%);margin:0 0 18px;border:1px solid #9caebb;border-radius:5px}}table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #dde5eb;overflow-wrap:anywhere}}th{{position:sticky;top:0;background:#edf2f6}}tr[hidden]{{display:none}}.bom-content>div{{max-height:none!important}}@media print{{input{{display:none}}body{{margin:0}}th{{position:static}}}}</style></head><body><input type="search" id="q" aria-label="Szukaj w BOM" placeholder="Szukaj części…"><details open>{content}</details><script>document.getElementById('q').addEventListener('input',e=>{{const q=e.target.value.toLocaleLowerCase('pl');for(const r of document.querySelectorAll('tbody tr'))r.hidden=!r.textContent.toLocaleLowerCase('pl').includes(q)}});</script></body></html>"#))
}
#[cfg(test)] mod tests {
 use super::*;
 #[test] fn independent_html_bom_without_csv(){let source="<h1>Zmiany</h1><details class=\"panel bom-panel\"><summary>BOM A</summary><table><tr><td>&lt;A&gt;</td></tr></table></details><details class=\"panel bom-panel\"><summary>BOM B</summary><table><tr><td>Osłona B</td></tr></table></details>";let a=bom_document(source,0).unwrap();let b=bom_document(source,1).unwrap();assert!(a.contains("&lt;A&gt;"));assert!(!a.contains("Osłona B"));assert!(b.contains("Osłona B"));assert!(!b.contains("&lt;A&gt;"));assert!(bom_document(source,2).is_err());assert!(bom_document("Brak zestawienia",0).is_err());}
}
