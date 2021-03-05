use crate::ansible::error::*;
use std::fmt;
use std::cmp::Ordering;
use std::str::FromStr;

// Note: Ord doesn't really make sense for Stage alone.
// An alpha is newer than, or older than, a GA release, depending on which
// versions are being compared. So we implement Ord on AnsibleVersion itself
// instead.
#[derive(Eq, PartialEq, Copy, Clone, Debug)]
pub enum Stage {
    /// General Availability release
    GA,
    /// Release Candidate
    RC(u8),
    /// Alpha (currently not used by Ansible)
    A(u8),
    /// Beta
    B(u8),
}

impl fmt::Display for Stage {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let out = match self {
            Stage::GA => "".to_string(),
            Stage::RC(v) => format!("rc{}", v),
            Stage::A(v) => format!("a{}", v),
            Stage::B(v) => format!("b{}", v),
        };
        write!(f, "{}", out)
    }
}

#[derive(Eq, PartialEq, Copy, Clone, Debug)]
pub struct Version {
    x: u8,
    y: u8,
    z: u8,
    stage: Stage,
}

impl Version {
    fn new(x: u8, y: u8, z: u8, stage: Stage) -> Version {
        Version { x, y, z, stage }
    }
}

impl Ord for Version {
    fn cmp(&self, other: &Self) -> Ordering {
        if self.x != other.x {
            return self.x.cmp(&other.x);
        }
        if self.y != other.y {
            return self.y.cmp(&other.y);
        }
        if self.z != other.z {
            return self.z.cmp(&other.z);
        }
        // If we're still here, we compare stage only.
        // We have equal x.y.z numbers at this point.
        use Stage::*;
        match (self.stage, other.stage) {
            (GA, GA) => Ordering::Equal,
            (GA, _) => Ordering::Greater,
            (RC(_), GA) => Ordering::Less,
            (RC(ref sv), RC(ref ov)) => sv.cmp(ov),
            (RC(_), _) => Ordering::Greater,
            (A(ref sv), A(ref ov)) => sv.cmp(ov),
            (A(_), _) => Ordering::Less,
            (B(ref sv), B(ref ov)) => sv.cmp(ov),
            (B(_), A(_)) => Ordering::Greater,
            (B(_), _) => Ordering::Less,
        }
    }
}

impl PartialOrd for Version {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl fmt::Display for Version {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}.{}.{}{}", self.x, self.y, self.z, self.stage)
    }
}

impl FromStr for Version {
    type Err = ParseError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        fn to_u8(s: &&str) -> Option<u8> {
            s.parse::<u8>().ok()
        }

        fn to_z_and_stage(s: &&str) -> Option<(u8, Stage)> {
            // If it's fully numeric, this must be a GA release.
            if let Some(z) = s.parse::<u8>().ok() {
                return Some((z, Stage::GA))
            }

            let (vec, stage_con): (Vec<&str>, fn(u8) -> Stage) =
                if s.contains("rc") {
                    (s.split("rc").collect(), Stage::RC)
                } else if s.contains("b") {
                    (s.split("b").collect(), Stage::B)
                } else if s.contains("a") {
                    (s.split("a").collect(), Stage::A)
                } else {
                    return None
                };

            let z = vec.get(0).and_then(to_u8)?;
            let stage_rel = vec.get(1).and_then(to_u8)?;
            Some((z, stage_con(stage_rel)))
        }

        fn components_to_version(
            components: Vec<&str>,
        ) -> Option<Version> {
            let x = components.get(0).and_then(to_u8)?;
            let y = components.get(1).and_then(to_u8)?;
            let (z, stage) = components.get(2).and_then(to_z_and_stage)?;
            Some(Version::new(x, y, z, stage))
        }

        let components: Vec<&str> = s.split('.').collect();
        let version = components_to_version(components);
        version.ok_or(ParseError::new(s.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use super::Stage::*;

    #[test]
    #[allow(non_snake_case)]
    fn test_Version_FromStr() {
        assert_eq!(
            Version::from_str("2.10.0").unwrap(),
            Version::new(2, 10, 0, GA));
        assert_eq!(
            Version::from_str("2.10.3rc1").unwrap(),
            Version::new(2, 10, 3, RC(1)));
        assert_eq!(
            Version::from_str("2.10.3b1").unwrap(),
            Version::new(2, 10, 3, B(1)));
        assert_eq!(
            Version::from_str("2.10.3a6").unwrap(),
            Version::new(2, 10, 3, A(6)));
        assert_eq!(
            Version::from_str("2.10.3foo1").unwrap_err(),
            ParseError::new("2.10.3foo1".to_string()));
        assert_eq!(
            Version::from_str("2.-10.3rc1").unwrap_err(),
            ParseError::new("2.-10.3rc1".to_string()));
    }

    #[test]
    #[allow(non_snake_case)]
    fn test_Version_ordering() {
        assert!(Version::new(2, 8, 4, GA) == Version::new(2, 8, 4, GA));
        assert!(Version::new(2, 8, 4, GA) >= Version::new(2, 8, 4, GA));
        assert!(Version::new(2, 8, 4, GA) >= Version::new(2, 8, 4, A(3)));
        assert!(Version::new(2, 8, 3, GA) <= Version::new(2, 8, 4, GA));
        assert!(Version::new(2, 8, 3, GA) < Version::new(2, 8, 4, GA));
        assert!(Version::new(2, 8, 4, GA) < Version::new(2, 9, 10, RC(1)));
        assert!(Version::new(2, 12, 0, GA) > Version::new(2, 11, 99, GA));
        assert!(Version::new(2, 12, 0, GA) > Version::new(2, 11, 99, B(200)));
        assert!(Version::new(2, 12, 5, GA) > Version::new(2, 12, 4, B(200)));
        assert!(Version::new(2, 12, 5, GA) > Version::new(2, 12, 4, GA));

        assert!(Version::new(2, 11, 0, B(1)) == Version::new(2, 11, 0, B(1)));
        assert!(Version::new(2, 11, 0, B(2)) > Version::new(2, 11, 0, B(1)));
        assert!(Version::new(2, 11, 0, B(2)) < Version::new(2, 11, 0, B(3)));
        assert!(Version::new(2, 11, 0, B(2)) < Version::new(2, 11, 9, RC(3)));
        assert!(Version::new(2, 11, 0, B(2)) < Version::new(2, 11, 9, A(1)));
        assert!(Version::new(2, 11, 0, B(2)) > Version::new(2, 11, 0, A(1)));
        assert!(Version::new(2, 11, 0, B(2)) < Version::new(2, 11, 0, GA));
        assert!(Version::new(2, 11, 9, B(2)) < Version::new(2, 11, 9, RC(3)));

        assert!(Version::new(2, 11, 0, A(1)) < Version::new(2, 11, 0, B(1)));
        assert!(Version::new(2, 11, 0, A(1)) < Version::new(2, 11, 0, GA));
        assert!(Version::new(2, 11, 0, A(1)) < Version::new(2, 11, 0, A(2)));
        assert!(Version::new(2, 12, 0, A(1)) > Version::new(2, 11, 0, A(2)));
        assert!(Version::new(2, 12, 0, A(1)) > Version::new(2, 11, 0, A(1)));
        assert!(Version::new(2, 11, 0, A(1)) < Version::new(2, 11, 0, RC(3)));

        assert!(Version::new(2, 12, 5, RC(3)) < Version::new(2, 12, 6, GA));
        assert!(Version::new(2, 12, 5, RC(3)) > Version::new(2, 12, 5, B(3)));
        assert!(Version::new(2, 12, 5, RC(3)) == Version::new(2, 12, 5, RC(3)));
        assert!(Version::new(2, 12, 5, RC(3)) <= Version::new(2, 12, 5, RC(3)));
        assert!(Version::new(2, 12, 5, RC(5)) <= Version::new(2, 12, 5, RC(9)));
        assert!(Version::new(3, 12, 5, RC(3)) >= Version::new(2, 12, 5, RC(3)));
        assert!(Version::new(3, 12, 5, RC(3)) > Version::new(2, 12, 5, RC(3)));
        assert!(Version::new(3, 12, 5, RC(3)) < Version::new(9, 12, 5, RC(3)));
    }

    #[test]
    #[allow(non_snake_case)]
    fn test_Version_display() {
        assert_eq!(format!("{}", Version::new(2, 12, 5, GA)), "2.12.5");
        assert_eq!(format!("{}", Version::new(2, 12, 5, RC(1))), "2.12.5rc1");
        assert_eq!(format!("{}", Version::new(2, 11, 0, B(1))), "2.11.0b1");
        assert_eq!(format!("{}", Version::new(2, 11, 0, A(1))), "2.11.0a1");
    }
}
