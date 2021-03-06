use crate::ansible;
use serde_with::DeserializeFromStr;
use std::fmt;
use std::cmp::Ordering;
use std::str::FromStr;

// Note: Ord doesn't really make sense for Stage alone.
// An alpha is newer than, or older than, a GA release, depending on which
// versions are being compared. So we implement Ord on AnsibleVersion itself
// instead.
#[derive(Eq, PartialEq, Clone, Debug, Hash)]
pub enum Stage {
    /// General Availability release
    GA,
    /// Release Candidate
    RC(u8),
    /// Alpha (currently not used by Ansible)
    A(u8),
    /// Beta
    B(u8),
    /// dev?
    Dev(u8),
}

impl fmt::Display for Stage {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let out = match self {
            Stage::GA => "".to_string(),
            Stage::RC(v) => format!("rc{}", v),
            Stage::A(v) => format!("a{}", v),
            Stage::B(v) => format!("b{}", v),
            Stage::Dev(v) => format!("dev{}", v),
        };
        write!(f, "{}", out)
    }
}

/// Ansible versions are all over the place. Some old versions had just two
/// components in the version. Some had 4. Most have 3. Because of the
/// inconsistency, the version numbers are backed by a dynamically-sized vector
/// (and the stage is kept separately).
#[derive(Eq, PartialEq, Clone, Debug, DeserializeFromStr, Hash)]
pub struct Version {
    pub numbers: Vec<u8>,
    pub stage: Stage,
}

impl Version {
    pub fn new(numbers: Vec<u8>, stage: Stage) -> Version {
        Version { numbers, stage }
    }

    pub fn new3(x: u8, y: u8, z: u8, stage: Stage) -> Version {
        Version { numbers: vec![x, y, z], stage: stage }
    }
}

impl Ord for Version {
    fn cmp(&self, other: &Self) -> Ordering {
        fn drop_right_zeros(vec: Vec<u8>) -> Vec<u8> {
            vec
                .into_iter()
                .rev()
                .skip_while(|x| *x == 0)
                .collect::<Vec<u8>>()
                .into_iter()
                .rev()
                .collect()
        }

        let me = drop_right_zeros(self.numbers.clone());
        let notme = drop_right_zeros(other.numbers.clone());
        if me != notme {
            return me.cmp(&notme);
        }

        // If we're still here, we compare stage only.
        // We have equal x.y.z numbers at this point.
        use Stage::*;
        match (&self.stage, &other.stage) {
            (GA, GA) => Ordering::Equal,
            (GA, _) => Ordering::Greater,
            (RC(_), GA) => Ordering::Less,
            (RC(ref sv), RC(ref ov)) => sv.cmp(ov),
            (RC(_), _) => Ordering::Greater,
            (A(ref sv), A(ref ov)) => sv.cmp(ov),
            (A(_), Dev(_)) => Ordering::Greater,
            (A(_), _) => Ordering::Less,
            (B(ref sv), B(ref ov)) => sv.cmp(ov),
            (B(_), A(_)) => Ordering::Greater,
            (B(_), _) => Ordering::Less,
            (Dev(ref sv), Dev(ref ov)) => sv.cmp(ov),
            (Dev(_), _) => Ordering::Less,
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
        let nums = &self.numbers;
        write!(
            f,
            "{}{}",
            nums
                .into_iter()
                .map(|x| x.to_string())
                .collect::<Vec<String>>()
                .join("."),
            self.stage)
    }
}


impl FromStr for Version {
    type Err = ansible::Error;

    /// Parse an Ansible version number into something we can compare and
    /// (usually, but not always) output the same way it was originally given.
    ///
    /// NOTE: We do NOT aim to be a full
    /// [PEP440](https://www.python.org/dev/peps/pep-0440/) version parser, not
    /// even close. This parser will break with more complex things like "local"
    /// versions, or combining segments (Python considers `2.7.0rc1.post0.dev6`
    /// to be a valid version number).
    ///
    /// We implement the pieces that Ansible, ansible-base, and ansible-core use
    /// and nothing more. This could change some day (a separate library/project
    /// with full PEP440 parsing might make for an interesting side project),
    /// but for now, we expect Ansible/ansible-base/ansible-core versions to
    /// remain consistent and we only aim to handle those.
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        fn to_u8(s: &&str) -> Option<u8> {
            s.parse::<u8>().ok()
        }

        fn to_last_and_stage(s: &&str) -> Option<(u8, Stage)> {
            // If it's fully numeric, this must be a GA release.
            if let Some(last) = s.parse::<u8>().ok() {
                return Some((last, Stage::GA))
            }

            // Handle an edge case: There was a release in the past, 2.7.0.dev0,
            // which had a . before the stage. We treat this as: 2.7.0.0dev0,
            // which python `packaging` says is okay:
            //
            // In [1]: import packaging.version as v
            // In [2]: v.parse("2.7.0.dev0") == v.parse("2.7.0.0dev0")
            // Out[2]: True
            //
            // This unfortunately means that we lose: display(from_str(x)) == x
            // but this seems like the easiest way to deal with the edge case.
            // (It is worth noting that Python loses that identity too, but in
            // the opposite direction where they add the dot):
            //
            // In [3]: v.parse("2.7.0dev0")
            // Out[3]: <Version('2.7.0.dev0')>
            let input = format!(
                "{}{}",
                if s.starts_with(char::is_numeric) { "" } else { "0" },
                s);

            let (vec, stage_con): (Vec<&str>, fn(u8) -> Stage) =
                if input.contains("rc") {
                    (input.split("rc").collect(), Stage::RC)
                } else if input.contains("b") {
                    (input.split("b").collect(), Stage::B)
                } else if input.contains("a") {
                    (input.split("a").collect(), Stage::A)
                } else if input.contains("dev") {
                    (input.split("dev").collect(), Stage::Dev)
                } else {
                    return None
                };

            let last = vec.get(0).and_then(to_u8)?;
            let stage_rel = vec.get(1).and_then(to_u8)?;
            Some((last, stage_con(stage_rel)))
        }

        fn components_to_version(
            components: Vec<&str>,
        ) -> Option<Version> {
            let (last, nums) = components.split_last()?;
            // mut because we need to add, e.g.,  the '3' of '3rc1' to it.
            let mut num_comps: Vec<u8> =
                nums
                .into_iter()
                .map(to_u8)
                .collect::<Option<Vec<u8>>>()?;
            let (last_num, stage) = to_last_and_stage(last)?;
            num_comps.push(last_num);
            Some(Version::new(num_comps, stage))
        }

        let components: Vec<&str> = s.split('.').collect();
        let version = components_to_version(components);
        version.ok_or(ansible::Error::parse_error(s.to_string()))
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
            Version::new3(2, 10, 0, GA));
        assert_eq!(
            Version::from_str("2.10.3rc1").unwrap(),
            Version::new3(2, 10, 3, RC(1)));
        assert_eq!(
            Version::from_str("2.10.3b1").unwrap(),
            Version::new3(2, 10, 3, B(1)));
        assert_eq!(
            Version::from_str("2.10.3a6").unwrap(),
            Version::new3(2, 10, 3, A(6)));
        assert_eq!(
            Version::from_str("2.10.3foo1").unwrap_err(),
            ansible::Error::parse_error("2.10.3foo1".to_string()));
        assert_eq!(
            Version::from_str("2.-10.3rc1").unwrap_err(),
            ansible::Error::parse_error("2.-10.3rc1".to_string()));
        assert_eq!(
            Version::from_str("2.10.3dev1").unwrap(),
            Version::new3(2, 10, 3, Dev(1)));
        assert_eq!(
            Version::from_str("2.10.3.dev1").unwrap(),
            Version::new(vec![2, 10, 3, 0], Dev(1)));
    }

    #[test]
    #[allow(non_snake_case)]
    fn test_Version_ordering() {
        assert!(Version::new3(2, 8, 4, GA) == Version::new3(2, 8, 4, GA));
        assert!(Version::new3(2, 8, 4, GA) >= Version::new3(2, 8, 4, GA));
        assert!(Version::new3(2, 8, 4, GA) >= Version::new3(2, 8, 4, A(3)));
        assert!(Version::new3(2, 8, 3, GA) <= Version::new3(2, 8, 4, GA));
        assert!(Version::new3(2, 8, 3, GA) < Version::new3(2, 8, 4, GA));
        assert!(Version::new3(2, 8, 4, GA) < Version::new3(2, 9, 10, RC(1)));
        assert!(Version::new3(2, 12, 0, GA) > Version::new3(2, 11, 99, GA));
        assert!(Version::new3(2, 12, 0, GA) > Version::new3(2, 11, 99, B(200)));
        assert!(Version::new3(2, 12, 5, GA) > Version::new3(2, 12, 4, B(200)));
        assert!(Version::new3(2, 12, 5, GA) > Version::new3(2, 12, 4, GA));

        assert!(Version::new3(2, 11, 0, B(1)) == Version::new3(2, 11, 0, B(1)));
        assert!(Version::new3(2, 11, 0, B(2)) > Version::new3(2, 11, 0, B(1)));
        assert!(Version::new3(2, 11, 0, B(2)) < Version::new3(2, 11, 0, B(3)));
        assert!(Version::new3(2, 11, 0, B(2)) < Version::new3(2, 11, 9, RC(3)));
        assert!(Version::new3(2, 11, 0, B(2)) < Version::new3(2, 11, 9, A(1)));
        assert!(Version::new3(2, 11, 0, B(2)) > Version::new3(2, 11, 0, A(1)));
        assert!(Version::new3(2, 11, 0, B(2)) < Version::new3(2, 11, 0, GA));
        assert!(Version::new3(2, 11, 9, B(2)) < Version::new3(2, 11, 9, RC(3)));

        assert!(Version::new3(2, 11, 0, A(1)) < Version::new3(2, 11, 0, B(1)));
        assert!(Version::new3(2, 11, 0, A(1)) < Version::new3(2, 11, 0, GA));
        assert!(Version::new3(2, 11, 0, A(1)) < Version::new3(2, 11, 0, A(2)));
        assert!(Version::new3(2, 12, 0, A(1)) > Version::new3(2, 11, 0, A(2)));
        assert!(Version::new3(2, 12, 0, A(1)) > Version::new3(2, 11, 0, A(1)));
        assert!(Version::new3(2, 11, 0, A(1)) < Version::new3(2, 11, 0, RC(3)));

        assert!(Version::new3(2, 12, 5, RC(3)) < Version::new3(2, 12, 6, GA));
        assert!(Version::new3(2, 12, 5, RC(3)) > Version::new3(2, 12, 5, B(3)));
        assert!(Version::new3(2, 12, 5, RC(3)) == Version::new3(2, 12, 5, RC(3)));
        assert!(Version::new3(2, 12, 5, RC(3)) <= Version::new3(2, 12, 5, RC(3)));
        assert!(Version::new3(2, 12, 5, RC(5)) <= Version::new3(2, 12, 5, RC(9)));
        assert!(Version::new3(3, 12, 5, RC(3)) >= Version::new3(2, 12, 5, RC(3)));
        assert!(Version::new3(3, 12, 5, RC(3)) > Version::new3(2, 12, 5, RC(3)));
        assert!(Version::new3(3, 12, 5, RC(3)) < Version::new3(9, 12, 5, RC(3)));

        assert!(Version::new3(3, 12, 5, Dev(3)) < Version::new3(9, 12, 5, RC(3)));
        assert!(Version::new3(3, 12, 5, Dev(3)) == Version::new3(3, 12, 5, Dev(3)));
        assert!(Version::new3(3, 12, 5, Dev(3)) < Version::new3(9, 12, 5, A(3)));

        assert!(Version::new(vec![2, 7, 0, 0], Dev(0)) < Version::new(vec![2, 7, 0], GA));
    }

    #[test]
    #[allow(non_snake_case)]
    fn test_Version_display() {
        assert_eq!(format!("{}", Version::new3(2, 12, 5, GA)), "2.12.5");
        assert_eq!(format!("{}", Version::new3(2, 12, 5, RC(1))), "2.12.5rc1");
        assert_eq!(format!("{}", Version::new3(2, 11, 0, B(1))), "2.11.0b1");
        assert_eq!(format!("{}", Version::new3(2, 11, 0, A(1))), "2.11.0a1");
        assert_eq!(format!("{}", Version::new3(2, 11, 0, Dev(1))), "2.11.0dev1");
    }
}
