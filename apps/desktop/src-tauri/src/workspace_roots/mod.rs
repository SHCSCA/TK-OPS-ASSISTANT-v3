pub mod commands;
mod logging;
mod registry;
mod types;
mod validation;

pub use registry::WorkspaceRootRegistry;
pub(crate) use types::ResolvedWorkspaceRoot;
