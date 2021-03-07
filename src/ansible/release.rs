use crate::ansible;
use crate::ansible::Product;
use crate::ansible::Stage;
use crate::ansible::Version;
use crate::pypi;

use chrono::prelude::*;
use chrono::Duration;
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

    /// The next release date is calculated by going back four days before the
    /// current upload (giving us 4 days leeway), and then finding the "3rd next
    /// Monday" (or "1st next Monday" for RC).
    pub fn guess_next_date(&self) -> DateTime<Utc> {
        let four_days_prior = self.timestamp - Duration::days(4);
        // 7 because num_days_from_monday() is 0-indexed. Monday is 0.
        let days_to_shift =
            7 - four_days_prior.date().weekday().num_days_from_monday();
        let weeks_to_shift = match self.version.stage {
            Stage::RC(_) => Duration::weeks(1),
            _ => Duration::weeks(3),
        };
        four_days_prior + weeks_to_shift + Duration::days(days_to_shift.into())
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_next_date_ga() {
        let date = DateTime::parse_from_rfc3339("2021-02-18T23:11:08.212573Z").unwrap();
        let expected = DateTime::parse_from_rfc3339("2021-03-08T23:11:08.212573Z").unwrap();

        let utcdate = DateTime::<Utc>::from(date);
        let utcexpected = DateTime::<Utc>::from(expected);

        let release = Release::new(
            Product::AnsibleBase,
            Version::new3(2, 10, 6, Stage::GA),
            utcdate);
        let nextdate = release.guess_next_date();
        assert_eq!(nextdate, utcexpected);
    }

    #[test]
    fn test_next_date_rc() {
        let date = DateTime::parse_from_rfc3339("2021-03-08T23:11:08.212573Z").unwrap();
        let expected = DateTime::parse_from_rfc3339("2021-03-15T23:11:08.212573Z").unwrap();

        let utcdate = DateTime::<Utc>::from(date);
        let utcexpected = DateTime::<Utc>::from(expected);

        let release = Release::new(
            Product::AnsibleBase,
            Version::new3(2, 10, 6, Stage::RC(1)),
            utcdate);
        let nextdate = release.guess_next_date();
        assert_eq!(nextdate, utcexpected);
    }
}
