use std::error::Error;
use std::fmt;

#[derive(Debug, Eq, PartialEq)]
pub struct AnsibleParseError {
    input: String,
}

impl AnsibleParseError {
    pub fn new(input: String) -> AnsibleParseError {
        AnsibleParseError { input }
    }
}

impl fmt::Display for AnsibleParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Failed to parse: {}", self.input)
    }
}

impl Error for AnsibleParseError {}
