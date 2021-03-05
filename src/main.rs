#[macro_use]
extern crate lazy_static;

use tera::Context;
use tera::Tera;
use std::{error::Error, fs, io};
use std::path::{Path, PathBuf};

mod ansible;

lazy_static! {
    pub static ref TEMPLATES: Tera =
        match Tera::new("src/templates/*.html") {
            Ok(t) => t,
            Err(e) => {
                println!("Parse error: {}", e);
                ::std::process::exit(1);
            }
        };
}

fn write_template_file(
    outpath: PathBuf,
    res: Result<String, tera::Error>) {
    match res {
        Ok(s) => {
            print!("Rendering {}...", outpath.display());
            match fs::write(outpath, s) {
                Ok(_) => println!("Done!"),
                Err(e) => {
                    println!("Write error: {}", e);
                    ::std::process::exit(1);
                }
            };
        }
        Err(e) => {
            println!("Render error: {}", e);
            let mut cause = e.source();
            while let Some(e) = cause {
                println!("Reason: {}", e);
                cause = e.source();
            }
            ::std::process::exit(1);
        }
    };
}

fn index() -> Context {
    let mut context = Context::new();
    context.insert("pagename", &"index");
    context
}

fn unimplemented() -> Context {
    Context::new()
}

fn main() -> io::Result<()> {
    let path = Path::new("out/");
    fs::create_dir_all(path)?;

    let templates: Vec<(&str, fn() -> tera::Context)> = vec![
        ("index.html", index),
        ("ci.html", unimplemented),
        ("announcement.html", unimplemented),
        ("aut.html", unimplemented),
        ("backports.html", unimplemented),
        ("ci.html", unimplemented),
        ("cves.html", unimplemented),
        ("dependencies.html", unimplemented),
        ("issues.html", unimplemented),
        ("packages.html", unimplemented),
        ("ppa.html", unimplemented),
    ];

    let mut common_context = Context::new();
    common_context.insert("pagename", "unimplemented");

    for (filename, func) in templates.iter() {
        let mut ctx = common_context.clone();
        ctx.extend(func());

        write_template_file(
            path.join(filename),
            TEMPLATES.render(filename, &ctx));
    }

    Ok(())
}
