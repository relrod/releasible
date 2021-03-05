use std::error::Error;
use std::fmt;

#[derive(Debug, Eq, PartialEq)]
pub struct ParseError {
    input: String,
}

impl ParseError {
    pub fn new(input: String) -> ParseError {
        ParseError { input }
    }
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Failed to parse: {}", self.input)
    }
}

impl Error for ParseError {}
