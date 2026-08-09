#[cfg(windows)]
use std::{error::Error, io};

#[cfg(windows)]
use windows_sys::Win32::UI::WindowsAndMessaging::{
    GetWindowLongPtrW, SetWindowLongPtrW, SetWindowPos, GWL_STYLE, SWP_FRAMECHANGED,
    SWP_NOACTIVATE, SWP_NOMOVE, SWP_NOSIZE, SWP_NOZORDER, WS_OVERLAPPEDWINDOW, WS_POPUP,
};

#[cfg(windows)]
pub fn ensure_standard_controls(window: &tauri::WebviewWindow) -> Result<(), Box<dyn Error>> {
    window.set_decorations(true)?;
    window.set_resizable(true)?;
    window.set_maximizable(true)?;
    window.set_minimizable(true)?;
    window.set_closable(true)?;

    let hwnd = window.hwnd()?.0;
    unsafe {
        let current_style = GetWindowLongPtrW(hwnd, GWL_STYLE);
        let required_style = WS_OVERLAPPEDWINDOW as isize;
        let standard_style = (current_style & !(WS_POPUP as isize)) | required_style;
        SetWindowLongPtrW(hwnd, GWL_STYLE, standard_style);
        let updated_style = GetWindowLongPtrW(hwnd, GWL_STYLE);
        if updated_style & required_style != required_style
            || updated_style & WS_POPUP as isize != 0
        {
            return Err(io::Error::other("主窗口标准控制样式未生效").into());
        }
        let refreshed = SetWindowPos(
            hwnd,
            std::ptr::null_mut(),
            0,
            0,
            0,
            0,
            SWP_FRAMECHANGED | SWP_NOACTIVATE | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER,
        );
        if refreshed == 0 {
            return Err(io::Error::last_os_error().into());
        }
    }
    Ok(())
}
