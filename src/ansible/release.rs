use crate::ansible;
use crate::ansible::Product;
use crate::ansible::Version;
use crate::pypi;

use chrono::prelude::*;
use std::fmt;
use serde::Serialize;
use std::ops::RangeBounds;

/// Represents a given release of an Ansible product such as `ansible`,
/// `ansible-base`, or `ansible-core`.
#[derive(Eq, PartialEq, Clone, Debug, Serialize)]
pub struct Release {
    product: Product,
    version: Version,
    timestamp: DateTime<Utc>,
}

impl Release {
    pub fn new(
        product: Product,
        version: Version,
        timestamp: DateTime<Utc>
    ) -> Release {
        Release { product, version, timestamp }
    }

    // TODO: Maybe move pypi::client::* here? And/or figure out a better
    // deserialization. I'm not sure what the pattern should look like. Right
    // now we serde-deserialize to some PyPI API-specific types in pypi::client,
    // rather than deserializing directly into Releases here, and then map those
    // types into our Release defined above.
    /// Given a product and version range, generate a Release for the latest
    /// available release that PyPI knows about.
    pub async fn latest_from_pypi_response<R>(
        product: Product,
        range: R,
    ) -> Result<Release, ansible::Error>
    where
        R: RangeBounds<Version>,
    {
        let product_str = format!("{}", product);
        let resp = pypi::client::get_releases(&product_str).await?;
        let (version, releases) =
            resp
            .releases
            .range(range)
            .into_iter()
            .into_iter()
            .next_back()
            .ok_or(ansible::Error::NoVersionFound)?;

        // Pull out a release artifact (assuming one exists), and grab its
        // upload time. Multiple artifacts could be uploaded at different times,
        // but for our purposes, we just need a rough idea/date.
        let artifact = releases.get(0).ok_or(ansible::Error::NoVersionFound)?;

        Ok(
            Release::new(
                product,
                version.clone(),
                artifact.upload_time_iso_8601))
    }
}

impl fmt::Display for Release {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "<Release: {} {} on {}>",
            self.product,
            self.version,
            self.timestamp)
    }
}
