use crate::ansible::Version;
use chrono::prelude::*;
use serde::Deserialize;
use std::collections::BTreeMap;

#[derive(Debug, Deserialize)]
pub struct Response {
    pub releases: BTreeMap<Version, Vec<Release>>,
}

#[derive(Debug, Deserialize)]
pub struct Release {
    pub size: u64,
    pub upload_time_iso_8601: DateTime<Utc>,
}

pub async fn get_releases(
    package: &str
) -> Result<Response, reqwest::Error> {
    let url = format!("https://pypi.org/pypi/{}/json", package);
    let resp: Response = reqwest::get(&url)
        .await?
        .json()
        .await?;
    Ok(resp)
}
