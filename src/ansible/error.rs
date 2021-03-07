use std::error::Error as StdError;
use std::fmt;

#[derive(Debug)]
pub enum Error {
    ParseError(String),
    NoVersionFound,
    ReqwestError(reqwest::Error),
}

impl Error {
    #[inline]
    pub fn parse_error(input: String) -> Error {
        Error::ParseError(input)
    }

    pub fn get_parse_error(&self) -> Option<String> {
        match self {
            Error::ParseError(s) => Some(s.to_string()),
            _ => None,
        }
    }

    pub fn is_parse_error(&self) -> bool {
        match self {
            Error::ParseError(_) => true,
            _ => false,
        }
    }

    pub fn is_no_version_found(&self) -> bool {
        match self {
            Error::NoVersionFound => true,
            _ => false,
        }
    }

    pub fn is_reqwest_error(&self) -> bool {
        match self {
            Error::ReqwestError(_) => true,
            _ => false,
        }
    }
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::ParseError(input) => write!(f, "Failed to parse: {}", input),
            Error::NoVersionFound => write!(f, "No such version(s) found"),
            Error::ReqwestError(err) => write!(f, "HTTP (Reqwest) error: {}", err),
        }
    }
}

impl StdError for Error {
    fn source(&self) -> Option<&(dyn StdError + 'static)> {
        match self {
            Error::ReqwestError(e) => Some(e),
            _ => None,
        }
    }
}

impl From<reqwest::Error> for Error {
    #[inline]
    fn from(err: reqwest::Error) -> Error {
        Error::ReqwestError(err)
    }
}
