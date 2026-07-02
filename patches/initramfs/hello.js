#!/node
// Minimal example of a JavaScript process running inside Linux/Wasm.

const msg = "Hello from JavaScript process!\n";
const buf = os.alloc(msg.length);
os.writeString(buf, msg);
os.syscall(os.SYS_write, 1, buf, msg.length);
os.syscall(os.SYS_exit, 0);
