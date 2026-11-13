const { spawn, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log("======================================================================");
console.log("⚡ CYBERSHORTS AI: PTERODACTYL NODE/CONTAINER LAUNCHER");
console.log("======================================================================\n");

// 1. Configure Environment Paths
const homeDir = process.env.HOME || '/home/container';
const userBin = path.join(homeDir, '.local', 'bin');
const ffmpegStaticDir = path.join(__dirname, 'node_modules', 'ffmpeg-static');

process.env.PATH = `${userBin}:/home/container/.local/bin:${ffmpegStaticDir}:${process.env.PATH}`;
process.env.PYTHONPATH = `${__dirname}:${process.env.PYTHONPATH || ''}`;
process.env.PYTHONUNBUFFERED = "1";

// 2. Detect Python binary
let pythonCmd = null;
for (const cmd of ['python3', 'python']) {
  try {
    const version = execSync(`${cmd} --version`, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'ignore'] });
    console.log(`[+] Detected Python runtime: ${version.trim()} (${cmd})`);
    pythonCmd = cmd;
    break;
  } catch (err) {}
}

if (!pythonCmd) {
  console.error("\n[!] CRITICAL ERROR: Python is not installed in this container image.");
  console.error("[!] In Q-Fi Cloud, you can change the server image to Python or install python3.");
  process.exit(1);
}

// 3. Ensure PIP is available (Bootstrap if missing)
let pipAvailable = false;
try {
  execSync(`${pythonCmd} -m pip --version`, { stdio: 'ignore' });
  pipAvailable = true;
  console.log("[+] pip is verified and ready.");
} catch (e) {
  console.log("[*] pip module is not yet installed in Python. Initiating automatic bootstrap...");
  const getPipScript = path.join(__dirname, 'get-pip.py');

  if (fs.existsSync(getPipScript)) {
    console.log(`[*] Executing local bootstrap script: ${getPipScript}`);
    try {
      execSync(`${pythonCmd} "${getPipScript}" --break-system-packages --no-warn-script-location`, { stdio: 'inherit' });
      pipAvailable = true;
      console.log("[+] pip bootstrapped successfully!");
    } catch (err1) {
      console.log("[*] Retrying pip bootstrap with --user flag...");
      try {
        execSync(`${pythonCmd} "${getPipScript}" --user --break-system-packages --no-warn-script-location`, { stdio: 'inherit' });
        pipAvailable = true;
        console.log("[+] pip bootstrapped successfully with --user!");
      } catch (err2) {
        console.error("[!] Failed to bootstrap pip:", err2.message);
      }
    }
  } else {
    console.error("[!] Warning: get-pip.py was not found in directory.");
  }
}

// 4. Install / Verify Python Dependencies
console.log("\n[*] Verifying Python application dependencies...");
let depsReady = false;
try {
  execSync(`${pythonCmd} -c "import schedule, requests, edge_tts, PIL, uvicorn, fastapi"`, { stdio: 'ignore' });
  depsReady = true;
  console.log("[+] All Python dependencies are satisfied! (schedule, edge-tts, pillow, fastapi, etc.)");
} catch (e) {
  depsReady = false;
}

if (!depsReady) {
  const reqFile = path.join(__dirname, 'requirements.txt');
  if (fs.existsSync(reqFile)) {
    console.log("[*] Installing required packages from requirements.txt...");
    try {
      execSync(`${pythonCmd} -m pip install -r "${reqFile}" --break-system-packages --no-warn-script-location`, { stdio: 'inherit' });
      console.log("[+] Dependencies installed successfully!");
    } catch (err1) {
      console.log("[*] Retrying pip install with --user flag...");
      try {
        execSync(`${pythonCmd} -m pip install --user -r "${reqFile}" --break-system-packages --no-warn-script-location`, { stdio: 'inherit' });
        console.log("[+] Dependencies installed successfully via --user!");
      } catch (err2) {
        console.error("[!] Dependency installation encountered an error:", err2.message);
      }
    }
  } else {
    console.warn("[!] requirements.txt not found. Continuing with installed modules...");
  }
}

// 5. Verify FFmpeg Availability
console.log("\n[*] Verifying FFmpeg multimedia engine...");
let ffmpegReady = false;
try {
  execSync('ffmpeg -version', { stdio: 'ignore' });
  ffmpegReady = true;
  console.log("[+] FFmpeg is available in system PATH.");
} catch (e) {
  const staticBin = path.join(ffmpegStaticDir, 'ffmpeg');
  if (fs.existsSync(staticBin)) {
    try { fs.chmodSync(staticBin, 0o755); } catch (err) {}
    process.env.PATH = `${ffmpegStaticDir}:${process.env.PATH}`;
    ffmpegReady = true;
    console.log(`[+] Bundled static FFmpeg active at: ${staticBin}`);
  }
}

if (!ffmpegReady) {
  console.log("[*] Note: If FFmpeg is not in container image, npm install will download static ffmpeg on next restart.");
}

// 6. Launch Master Automation Daemon
console.log("\n======================================================================");
console.log("🚀 STARTING CYBERSHORTS AI AUTONOMOUS DAEMON");
console.log("======================================================================\n");

const daemon = spawn(pythonCmd, ['run.py', '--daemon'], {
  stdio: 'inherit',
  shell: false,
  env: process.env
});

daemon.on('error', (err) => {
  console.error("[!] Failed to spawn Python process:", err);
  process.exit(1);
});

daemon.on('close', (code) => {
  console.log(`\n[!] CyberShorts AI exited with code: ${code}`);
  process.exit(code || 0);
});
