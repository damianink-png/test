use std::fs::File;
use std::io::{self, Read, Seek, SeekFrom};
use std::path::Path;

pub fn read(path: &Path, count: usize) -> io::Result<String> {
    read_counted(path, count).map(|(text, _)| text)
}

fn read_counted(path: &Path, count: usize) -> io::Result<(String, u64)> {
    if count == 0 { return Ok((String::new(), 0)); }
    let mut file = File::open(path)?;
    let mut offset = file.metadata()?.len();
    let mut bytes = Vec::new();
    let mut read_bytes = 0;
    let mut block = 8192_u64;
    loop {
        let size = offset.min(block) as usize;
        offset -= size as u64;
        file.seek(SeekFrom::Start(offset))?;
        let mut chunk = vec![0; size];
        file.read_exact(&mut chunk)?;
        read_bytes += size as u64;
        chunk.extend_from_slice(&bytes);
        bytes = chunk;
        // A first partial line may accidentally parse as valid JSON. Ignore
        // it until its beginning is read, also avoiding partial UTF-8 input.
        let start = if offset == 0 { 0 } else {
            bytes.iter().position(|b| *b == b'\n').map(|i| i + 1).unwrap_or(bytes.len())
        };
        let text = String::from_utf8_lossy(&bytes[start..]);
        let valid = text.lines().rev().filter(|line| serde_json::from_str::<serde_json::Value>(line).is_ok()).take(count).count();
        if valid >= count || offset == 0 { return Ok((text.into_owned(), read_bytes)); }
        block = block.saturating_mul(2);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn valid(text: &str) -> Vec<serde_json::Value> {
        text.lines().rev().filter_map(|s| serde_json::from_str(s).ok()).take(100).collect()
    }
    #[test]
    fn tail_matches_full_reader_and_reads_less_data() {
        let path = std::env::temp_dir().join(format!("dscompare-tail-large-{}.jsonl", std::process::id()));
        let full = (0..10000).map(|i| format!("{{\"tekst\":\"Zażółć gęślą {i}\"}}\r\n")).collect::<String>();
        std::fs::write(&path, &full).unwrap();
        let (tail, bytes) = read_counted(&path, 100).unwrap();
        assert_eq!(valid(&tail), valid(&full));
        assert!(bytes < full.len() as u64 / 10);
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn malformed_and_partial_lines_do_not_hide_valid_history() {
        let path = std::env::temp_dir().join(format!("dscompare-tail-partial-{}.jsonl", std::process::id()));
        let mut full = (0..300).map(|i| format!("{{\"tekst\":\"Łódź {i}\"}}\ninvalid\n")).collect::<String>();
        full.push_str("{\"tekst\":\"unfinished");
        std::fs::write(&path, &full).unwrap();
        assert_eq!(valid(&read(&path, 100).unwrap()), valid(&full));
        std::fs::write(&path, "").unwrap();
        assert_eq!(read(&path, 100).unwrap(), "");
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn long_single_unicode_event_is_preserved() {
        let path = std::env::temp_dir().join(format!("dscompare-tail-long-{}.jsonl", std::process::id()));
        let full = serde_json::json!({"tekst": "ż".repeat(25000)}).to_string();
        std::fs::write(&path, &full).unwrap();
        let (tail, bytes) = read_counted(&path, 100).unwrap();
        assert_eq!(valid(&tail), valid(&full));
        assert_eq!(bytes, full.len() as u64);
        std::fs::remove_file(path).unwrap();
    }

}
