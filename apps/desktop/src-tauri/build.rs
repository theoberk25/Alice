fn main() {
    println!("cargo:rerun-if-changed=src/biometric_camera.swift");
    println!("cargo:rerun-if-changed=Info.plist");
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("macos") {
        let out = std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap());
        let arch = if std::env::var("CARGO_CFG_TARGET_ARCH").as_deref() == Ok("aarch64") {
            "arm64"
        } else {
            "x86_64"
        };
        let status = std::process::Command::new("xcrun")
            .args(["swiftc", "src/biometric_camera.swift", "-o"])
            .arg(out.join("alice-biometric-camera"))
            .arg("-target")
            .arg(format!("{arch}-apple-macosx12.0"))
            .arg("-module-cache-path")
            .arg(out.join("swift-cache"))
            .args([
                "-framework",
                "AVFoundation",
                "-framework",
                "AppKit",
                "-framework",
                "CoreImage",
                "-Xlinker",
                "-sectcreate",
                "-Xlinker",
                "__TEXT",
                "-Xlinker",
                "__info_plist",
                "-Xlinker",
                "Info.plist",
            ])
            .status()
            .expect("Swift toolchain required for native biometric capture");
        assert!(
            status.success(),
            "Native biometric camera helper failed to compile"
        );
    }
    tauri_build::build()
}
