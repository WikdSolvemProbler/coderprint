//! A port of read_added_code's `git log -p` parser (handle and paths in generator/written.py) to Rust, for the
//! spike: reads a saved stream and writes every file record it finishes in the same canonical form as
//! reference.py. Usage: diffparse STREAM OUT
use std::fs::File;
use std::io::{BufRead, BufReader, Write};
use std::time::Instant;

/// Python's str.split() whitespace, for the characters that can reach it here.
fn py_space(c: char) -> bool {
    c.is_whitespace() || ('\x1c'..='\x1f').contains(&c)
}

fn lossy(b: &[u8]) -> String {
    String::from_utf8_lossy(b).into_owned()
}

/// git_path: a path as git prints it outside -z output, unquoted.
fn git_path(text: &str) -> String {
    let c: Vec<char> = text.chars().collect();
    if c.len() < 2 || c[0] != '"' || c[c.len() - 1] != '"' {
        return text.to_string();
    }
    let s = &c[1..c.len() - 1];
    let mut out: Vec<u8> = Vec::new();
    let mut i = 0;
    while i < s.len() {
        if s[i] == '\\' {
            let esc = s.get(i + 1).and_then(|e| match e {
                'a' => Some(7u8), 'b' => Some(8), 't' => Some(9), 'n' => Some(10), 'v' => Some(11),
                'f' => Some(12), 'r' => Some(13), '"' => Some(34), '\\' => Some(92), _ => None,
            });
            if let Some(e) = esc {
                out.push(e);
                i += 2;
                continue;
            }
            let oct = &s[(i + 1).min(s.len())..(i + 4).min(s.len())];
            if oct.len() == 3 && oct.iter().all(|d| ('0'..='7').contains(d)) {
                let v = oct.iter().fold(0u32, |n, d| n * 8 + (*d as u32 - '0' as u32));
                out.push((v & 0xFF) as u8);
                i += 4;
                continue;
            }
            return text.to_string();
        }
        let mut buf = [0u8; 4];
        out.extend_from_slice(s[i].encode_utf8(&mut buf).as_bytes());
        i += 1;
    }
    lossy(&out)
}

fn diff_path(text: &str, prefix: &str) -> Option<String> {
    let text = text.strip_suffix('\t').unwrap_or(text);
    if text == "/dev/null" {
        return None;
    }
    let path = git_path(text);
    Some(match path.strip_prefix(prefix) { Some(p) => p.to_string(), None => path })
}

/// The length in chars of the QUOTED string starting at c[0] == '"', closing quote included, or None.
fn quoted_len(c: &[char]) -> Option<usize> {
    if c.first() != Some(&'"') {
        return None;
    }
    let mut i = 1;
    while i < c.len() {
        match c[i] {
            '"' => return Some(i + 1),
            '\\' => {
                if i + 1 < c.len() && c[i + 1] != '\n' { i += 2 } else { return None }
            }
            _ => i += 1,
        }
    }
    None
}

fn header_paths(text: &str) -> (Option<String>, Option<String>) {
    let c: Vec<char> = text.chars().collect();
    let s = |a: usize, z: usize| -> String { c[a..z].iter().collect() };
    let mut pair: Option<(String, String)> = None;
    // (QUOTED) (.*)$
    if let Some(q) = quoted_len(&c) {
        if c.get(q) == Some(&' ') {
            pair = Some((git_path(&s(0, q)), git_path(&s(q + 1, c.len()))));
        }
    }
    // ([^"]*) (QUOTED)$
    if pair.is_none() {
        if let Some(at) = c.iter().position(|&x| x == '"') {
            if at >= 1 && c[at - 1] == ' ' && quoted_len(&c[at..]) == Some(c.len() - at) {
                pair = Some((git_path(&s(0, at - 1)), git_path(&s(at, c.len()))));
            }
        }
    }
    let (a, b) = match pair {
        Some(p) => p,
        None => {
            let half = c.len() / 2;
            let a = s(0, half);
            let b = if half + 1 <= c.len() { s(half + 1, c.len()) } else { String::new() };
            let tail = |x: &str| -> String { x.chars().skip(2).collect() };
            if c.len() % 2 == 0 || c.get(half) != Some(&' ') || tail(&a) != tail(&b) {
                return (None, None);
            }
            (a, b)
        }
    };
    match (a.strip_prefix("a/"), b.strip_prefix("b/")) {
        (Some(x), Some(y)) => (Some(x.to_string()), Some(y.to_string())),
        _ => (None, None),
    }
}

/// HUNK: @@ -a(,b)? +c(,d)? @@ at the line's start; numbers as int() would print them.
fn hunk(raw: &[u8]) -> Option<[String; 4]> {
    fn num(raw: &[u8], i: &mut usize) -> Option<String> {
        let st = *i;
        while *i < raw.len() && raw[*i].is_ascii_digit() { *i += 1 }
        if *i == st { return None }
        let d = std::str::from_utf8(&raw[st..*i]).unwrap().trim_start_matches('0');
        Some(if d.is_empty() { "0".to_string() } else { d.to_string() })
    }
    fn opt(raw: &[u8], i: &mut usize) -> Option<String> {
        if raw.get(*i) == Some(&b',') {
            let save = *i;
            *i += 1;
            match num(raw, i) { Some(n) => return Some(n), None => { *i = save; } }
        }
        None
    }
    let mut i = 0;
    if !raw.starts_with(b"@@ -") { return None }
    i += 4;
    let a = num(raw, &mut i)?;
    let b = opt(raw, &mut i).unwrap_or_else(|| "1".into());
    if !raw[i..].starts_with(b" +") { return None }
    i += 2;
    let c = num(raw, &mut i)?;
    let d = opt(raw, &mut i).unwrap_or_else(|| "1".into());
    if !raw[i..].starts_with(b" @@") { return None }
    Some([a, b, c, d])
}

struct Hunk { n: [String; 4], minus: Vec<Vec<u8>>, plus: Vec<Vec<u8>>, eol6: bool, eol7: bool }

#[derive(Default)]
struct FileRec {
    old_blob: Option<String>, new_blob: Option<String>, old_path: Option<String>, new_path: Option<String>,
    mode: Option<String>, binary: bool, hunks: Vec<Hunk>, labels: bool, created: bool, deleted: bool,
    from: Option<String>, to: Option<String>, binary_line: Option<String>,
    git_paths: (Option<String>, Option<String>),
}

// hunk_open: Python's s["hunk"] is not None; side: its s["side"], 0 for None
struct State { sha: Option<String>, merge: bool, parents: Vec<String>, file: Option<FileRec>, header: bool,
               hunk_open: bool, side: u8 }

fn field(out: &mut Vec<u8>, v: Option<&[u8]>) {
    match v {
        None => out.push(b'-'),
        Some(d) => { out.extend_from_slice(d.len().to_string().as_bytes()); out.push(b':'); out.extend_from_slice(d) }
    }
}

fn sfield(out: &mut Vec<u8>, v: &Option<String>) { field(out, v.as_deref().map(str::as_bytes)) }

fn paths(f: &mut FileRec) {
    if f.labels { return }
    let mut old = f.from.clone().filter(|x| !x.is_empty()).or_else(|| f.git_paths.0.clone());
    let mut new = f.to.clone().filter(|x| !x.is_empty()).or_else(|| f.git_paths.1.clone());
    if (old.is_none() || new.is_none()) && f.binary_line.as_deref().map_or(false, |x| !x.is_empty()) {
        let line = f.binary_line.as_deref().unwrap();
        if let Some(rest) = line.strip_prefix("Binary files ") {
            if let Some(mid) = rest.strip_suffix(" differ") {
                if let Some(k) = mid.rfind(" and ") {
                    let (m1, m2) = (&mid[..k], &mid[k + 5..]);
                    if !m1.contains('\n') && !m2.contains('\n') {
                        if old.as_deref().map_or(true, str::is_empty) { old = diff_path(m1, "a/") }
                        if new.as_deref().map_or(true, str::is_empty) { new = diff_path(m2, "b/") }
                    }
                }
            }
        }
    }
    f.old_path = if f.created { None } else { old };
    f.new_path = if f.deleted { None } else { new };
}

fn finish(s: &mut State, out: &mut Vec<u8>) {
    let Some(mut f) = s.file.take() else { return };
    paths(&mut f);
    out.extend_from_slice(b"F ");
    sfield(out, &s.sha);
    out.extend_from_slice(if s.merge { b" 1 " } else { b" 0 " });
    field(out, Some(s.parents.join(" ").as_bytes()));
    for v in [&f.old_blob, &f.new_blob, &f.old_path, &f.new_path, &f.mode, &f.from, &f.to] {
        out.push(b' ');
        sfield(out, v);
    }
    out.extend_from_slice(format!(" {}{}{}\n", f.binary as u8, f.created as u8, f.deleted as u8).as_bytes());
    for h in &f.hunks {
        out.extend_from_slice(format!("H {} {} {} {} {} {} {} {}\n", h.n[0], h.n[1], h.n[2], h.n[3], h.minus.len(),
                                      h.plus.len(), h.eol6 as u8, h.eol7 as u8).as_bytes());
        for line in h.minus.iter().chain(h.plus.iter()) {
            field(out, Some(line));
            out.push(b'\n');
        }
    }
}

fn is_blob_id(x: &str) -> bool {
    (x.len() == 40 || x.len() == 64) && x.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

fn handle_line(raw: &[u8], s: &mut State, out: &mut Vec<u8>) {
    if raw.first() == Some(&0) {
        finish(s, out);
        let ids: String = raw[1..].iter().map(|&b| if b < 128 { b as char } else { '\u{fffd}' }).collect();
        let ids: Vec<String> = ids.split(py_space).filter(|x| !x.is_empty()).map(String::from).collect();
        s.sha = ids.first().cloned();
        s.merge = ids.len() > 2;
        s.parents = ids.iter().skip(1).cloned().collect();
        s.header = false;
        return;
    }
    if raw.starts_with(b"diff --git ") {
        finish(s, out);
        s.header = true;
        s.hunk_open = false;
        s.side = 0;
        let text = lossy(&raw[11..]);
        let gp = header_paths(text.trim_end_matches('\n'));
        s.file = Some(FileRec { git_paths: gp, ..Default::default() });
        return;
    }
    let Some(f) = s.file.as_mut() else { return };
    if s.header {
        if raw.starts_with(b"@@") {
            s.header = false;
        } else {
            let line = lossy(raw);
            let line = line.trim_end_matches('\n');
            if let Some(rest) = line.strip_prefix("index ") {
                let fields: Vec<&str> = rest.split(' ').collect();
                let ids: Vec<&str> = fields[0].split("..").collect();
                if ids.len() == 2 && ids.iter().all(|x| is_blob_id(x)) {
                    f.old_blob = Some(ids[0].to_string());
                    f.new_blob = Some(ids[1].to_string());
                }
                if fields.len() > 1 { f.mode = Some(fields[1].to_string()) }
            } else if line.starts_with("new file mode ") || line.starts_with("new mode ")
                || line.starts_with("deleted file mode ") {
                f.mode = line.split(py_space).filter(|x| !x.is_empty()).last().map(String::from);
                f.created = f.created || line.starts_with("new file");
                f.deleted = f.deleted || line.starts_with("deleted");
            } else if line.starts_with("rename from ") || line.starts_with("copy from ") {
                f.from = Some(git_path(line.splitn(3, ' ').nth(2).unwrap()));
            } else if line.starts_with("rename to ") || line.starts_with("copy to ") {
                f.to = Some(git_path(line.splitn(3, ' ').nth(2).unwrap()));
            } else if let Some(p) = line.strip_prefix("--- ") {
                f.old_path = diff_path(p, "a/");
                f.labels = true;
            } else if let Some(p) = line.strip_prefix("+++ ") {
                f.new_path = diff_path(p, "b/");
                f.labels = true;
            } else if line.starts_with("Binary files ") {
                f.binary = true;
                f.binary_line = Some(line.to_string());
            }
            return;
        }
    }
    if raw.starts_with(b"@@") {
        if let Some(n) = hunk(raw) {
            f.hunks.push(Hunk { n, minus: vec![], plus: vec![], eol6: false, eol7: false });
            s.hunk_open = true;
        }
        s.side = 0;
        return;
    }
    if s.hunk_open {
        let h = f.hunks.last_mut().unwrap();
        let body = if raw.ends_with(b"\n") { &raw[1..raw.len() - 1] } else { &raw[1..] };
        match raw[0] {
            b'+' => { h.plus.push(body.to_vec()); s.side = 7 }
            b'-' => { h.minus.push(body.to_vec()); s.side = 6 }
            b'\\' if s.side != 0 => { if s.side == 6 { h.eol6 = true } else { h.eol7 = true } }
            _ => {}
        }
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut reader = BufReader::with_capacity(1 << 20, File::open(&args[1]).expect("stream"));
    let started = Instant::now();
    let mut s = State { sha: None, merge: false, parents: vec![], file: None, header: false, hunk_open: false, side: 0 };
    let mut out = Vec::with_capacity(1 << 24);
    let mut line = Vec::with_capacity(4096);
    loop {
        line.clear();
        if reader.read_until(b'\n', &mut line).expect("read") == 0 { break }
        handle_line(&line, &mut s, &mut out);
    }
    finish(&mut s, &mut out);
    let elapsed = started.elapsed();
    File::create(&args[2]).expect("out").write_all(&out).expect("write");
    eprintln!("rust parse: {:.3}s", elapsed.as_secs_f64());
}
