// Pin the browser language so rdmGettext output does not depend on the host locale.
Object.defineProperty(window.navigator, 'languages', {
    get: function() { return ['en-US', 'en']; }
});

// Mimics the context vars injected by the mako templates, which some modules
// read at load time (e.g. markdown.js builds WATERBUTLER_REGEX on require).
window.contextVars = {
    waterbutlerURL: 'http://localhost:7777/',
    osfURL: 'http://localhost:5000/',
    node: {
        urls: {
            mfr: 'http://localhost:7778/'
        }
    }
};
