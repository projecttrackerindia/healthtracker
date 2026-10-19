import type { CapacitorConfig } from '@capacitor/cli';

// The app is the live web app in a native shell. `server.url` points the WebView at the deployed site, so every
// release of the web app reaches phones without a store update; native pieces (Health Connect, notifications)
// are exposed to it through plugins. Set APP_URL at build time to point at staging.
const config: CapacitorConfig = {
  appId: 'com.thehealthtracker.app',
  appName: 'TheHealthTracker',
  webDir: 'www',
  server: {
    url: process.env.APP_URL || 'https://thehealthtracker.com/app',
    cleartext: false,
    androidScheme: 'https'
  },
  android: {
    allowMixedContent: false,
    backgroundColor: '#1d4fff'
  },
  plugins: {
    SplashScreen: { launchShowDuration: 800, backgroundColor: '#1d4fff', showSpinner: false },
    PushNotifications: { presentationOptions: ['badge', 'sound', 'alert'] }
  }
};

export default config;
