#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod app_paths;
mod native_window;
mod runtime_supervisor;
mod workspace_roots;

use std::sync::Arc;

use runtime_supervisor::{
    commands::{
        export_runtime_supervisor_diagnostics, get_runtime_connection,
        get_runtime_supervisor_diagnostics, get_runtime_supervisor_status, restart_runtime,
    },
    RuntimeSupervisor,
};
use tauri::Manager;
use workspace_roots::{
    commands::{
        describe_account_workspace_root, pick_account_workspace_root,
        reauthorize_account_workspace_root, revoke_account_workspace_root,
    },
    WorkspaceRootRegistry,
};

fn main() {
    let builder = tauri::Builder::default();
    #[cfg(windows)]
    let builder = builder.plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
        if let Some(supervisor) = app.try_state::<Arc<RuntimeSupervisor>>() {
            supervisor.record_startup_event("info", "desktop.single_instance_activation", None);
        }
        if let Some(window) = app.get_webview_window("main") {
            let restored = window.unminimize().is_ok();
            let shown = window.show().is_ok();
            let focused = window.set_focus().is_ok();
            let activated = restored && shown && focused;
            if !activated {
                eprintln!("TK-OPS 已运行，但主窗口激活失败。");
            }
        } else {
            eprintln!("TK-OPS 已运行，但主窗口尚不可用。");
        }
    }));

    let app = builder
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            get_runtime_connection,
            get_runtime_supervisor_status,
            get_runtime_supervisor_diagnostics,
            export_runtime_supervisor_diagnostics,
            restart_runtime,
            pick_account_workspace_root,
            describe_account_workspace_root,
            reauthorize_account_workspace_root,
            revoke_account_workspace_root
        ])
        .setup(|app| {
            #[cfg(windows)]
            if let Some(window) = app.get_webview_window("main") {
                native_window::ensure_standard_controls(&window)?;
            }
            let workspace_roots = WorkspaceRootRegistry::initialize(app.handle())?;
            app.manage(workspace_roots);
            let supervisor = Arc::new(RuntimeSupervisor::from_app(app.handle()));
            supervisor.record_startup_event("info", "desktop.setup_ready", None);
            app.manage(supervisor.clone());
            supervisor.start_initial();
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("无法构建 TK-OPS 桌面应用");

    app.run(|app_handle, event| {
        if let Some(supervisor) = app_handle.try_state::<Arc<RuntimeSupervisor>>() {
            match &event {
                tauri::RunEvent::WindowEvent { label, event, .. } => match event {
                    tauri::WindowEvent::CloseRequested { .. } => supervisor.record_startup_event(
                        "info",
                        &format!("desktop.window_close_requested.{label}"),
                        None,
                    ),
                    tauri::WindowEvent::Destroyed => supervisor.record_startup_event(
                        "info",
                        &format!("desktop.window_destroyed.{label}"),
                        None,
                    ),
                    _ => {}
                },
                tauri::RunEvent::ExitRequested { code, .. } => {
                    let error_code = code.map(|value| format!("DESKTOP_EXIT_CODE_{value}"));
                    supervisor.record_startup_event(
                        "info",
                        "desktop.exit_requested",
                        error_code.as_deref(),
                    );
                }
                tauri::RunEvent::Exit => {
                    supervisor.record_startup_event("info", "desktop.event_loop_exit", None);
                }
                _ => {}
            }
        }
        if matches!(
            event,
            tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit
        ) {
            if let Some(supervisor) = app_handle.try_state::<Arc<RuntimeSupervisor>>() {
                supervisor.shutdown();
            }
        }
    });
}
