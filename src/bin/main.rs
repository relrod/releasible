#[macro_use]
extern crate lazy_static;

use releasible::ansible;
use releasible::pypi;

use tera::Context;
use tera::Tera;
use std::future::Future;
use std::ops::Bound;
use std::{error::Error, fs, io};
use std::path::{Path, PathBuf};
use std::pin::Pin;

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

async fn index() -> Context {
    let mut context = Context::new();
    context.insert("pagename", &"index");

    let latest_28 =
        ansible::Release::latest_from_pypi_response(
            ansible::Product::Ansible,
            (Bound::Included(ansible::Version::new3(2, 8, 0, ansible::Stage::Dev(0))),
             Bound::Excluded(ansible::Version::new3(2, 9, 0, ansible::Stage::Dev(0)))))
        .await
        .ok();

    let latest_29 =
        ansible::Release::latest_from_pypi_response(
            ansible::Product::Ansible,
            (Bound::Included(ansible::Version::new3(2, 9, 0, ansible::Stage::Dev(0))),
             Bound::Excluded(ansible::Version::new3(2, 10, 0, ansible::Stage::Dev(0)))))
        .await
        .ok();

    let latest_210 =
        ansible::Release::latest_from_pypi_response(
            ansible::Product::AnsibleBase,
            (Bound::Included(ansible::Version::new3(2, 10, 0, ansible::Stage::Dev(0))),
             Bound::Excluded(ansible::Version::new3(2, 11, 0, ansible::Stage::Dev(0)))))
        .await
        .ok();

    let latest_211 =
        ansible::Release::latest_from_pypi_response(
            ansible::Product::AnsibleCore,
            (Bound::Included(ansible::Version::new3(2, 11, 0, ansible::Stage::Dev(0))),
             Bound::Excluded(ansible::Version::new3(2, 12, 0, ansible::Stage::Dev(0)))))
        .await
        .ok();

    context.insert("latest_28", &latest_28);
    context.insert("latest_29", &latest_29);
    context.insert("latest_210", &latest_210);
    context.insert("latest_211", &latest_211);
    let latest = vec![latest_28, latest_29, latest_210, latest_211];
    context.insert("releases", &latest);

    context
}

async fn unimplemented() -> Context {
    Context::new()
}

#[tokio::main]
async fn main() -> io::Result<()> {
    let path = Path::new("out/");
    fs::create_dir_all(path)?;

    let templates: Vec<(&str, fn() -> Pin<Box<dyn Future<Output = Context>>>)> = vec![
        ("index.html", || Box::pin(index())),
        ("ci.html", || Box::pin(unimplemented())),
        ("announcement.html", || Box::pin(unimplemented())),
        ("aut.html", || Box::pin(unimplemented())),
        ("backports.html", || Box::pin(unimplemented())),
        ("ci.html", || Box::pin(unimplemented())),
        ("cves.html", || Box::pin(unimplemented())),
        ("dependencies.html", || Box::pin(unimplemented())),
        ("issues.html", || Box::pin(unimplemented())),
        ("packages.html", || Box::pin(unimplemented())),
        ("ppa.html", || Box::pin(unimplemented())),
    ];

    let mut common_context = Context::new();
    common_context.insert("pagename", "unimplemented");

    for (filename, func) in templates.iter() {
        let mut ctx = common_context.clone();
        ctx.extend(func().await);

        write_template_file(
            path.join(filename),
            TEMPLATES.render(filename, &ctx));
    }
    Ok(())
}
