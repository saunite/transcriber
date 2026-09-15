// Stand-in for window.__TAURI__, injected before src/main.js runs
// (openspec/changes/add-automated-local-tests, design.md Decision 3).
// Tests read window.__fake.calls, set window.__fake.responses and fire app
// events with window.__fake.emit(name, payload).
(() => {
  const handlers = {};
  const fake = {
    calls: [],
    // cmd -> value, or {reject: "message"}
    responses: {
      get_platform: "linux",
      list_devices: [{ index: 0, name: "Fake Mic", max_input_channels: 1 }],
    },
    emit(name, payload) {
      for (const handler of handlers[name] ?? []) handler({ event: name, payload });
    },
  };
  window.__fake = fake;

  const asyncNoop = () => Promise.resolve();
  window.__TAURI__ = {
    core: {
      invoke(cmd, args) {
        fake.calls.push({ cmd, args });
        const response = fake.responses[cmd];
        if (response && typeof response === "object" && "reject" in response) {
          return Promise.reject(response.reject);
        }
        return Promise.resolve(response);
      },
    },
    event: {
      listen(name, handler) {
        (handlers[name] ??= []).push(handler);
        return Promise.resolve(() => {
          handlers[name] = handlers[name].filter((h) => h !== handler);
        });
      },
    },
    app: { getVersion: () => Promise.resolve("0.1.0") },
    dialog: { open: () => Promise.resolve(null), save: () => Promise.resolve(null) },
    // Every window method is an async no-op, so new chrome calls need no listing.
    window: { getCurrentWindow: () => new Proxy({}, { get: () => asyncNoop }) },
    path: {
      documentDir: () => Promise.resolve("/home/tester/Documents"),
      homeDir: () => Promise.resolve("/home/tester"),
      join: (...parts) => Promise.resolve(parts.join("/").replace(/\/+/g, "/")),
      isAbsolute: (p) => Promise.resolve(p.startsWith("/")),
    },
  };
})();
