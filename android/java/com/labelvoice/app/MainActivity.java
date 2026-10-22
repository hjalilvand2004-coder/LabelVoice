package com.labelvoice.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.ValueCallback;

import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;

/**
 * LabelVoice — برچسب‌خوان هوشمند دارو و محصولات
 *
 * WebView wrapper around the fully-offline PWA bundled in assets/.
 * Serves https://appassets.local/ from the APK assets via
 * shouldInterceptRequest, so the web app runs in a secure context with
 * everything local: Tesseract.js (WASM) + Persian/English language data.
 * No Python, no server, no internet required.
 */
public class MainActivity extends Activity {

    private static final String HOST = "appassets.local";
    private static final String START_URL = "https://appassets.local/index.html";
    private static final int FILE_CHOOSER_CODE = 1001;

    private WebView webView;
    private ValueCallback<Uri[]> filePathCallback;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        setContentView(webView);

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return serveAsset(request.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri url = request.getUrl();
                if (HOST.equals(url.getHost())) {
                    return false; // keep in-app
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, url)); // external links in browser
                } catch (Exception ignored) {
                }
                return true;
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                                             FileChooserParams params) {
                if (filePathCallback != null) {
                    filePathCallback.onReceiveValue(null);
                }
                filePathCallback = callback;
                try {
                    Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    intent.setType("image/*");
                    startActivityForResult(
                            Intent.createChooser(intent, "انتخاب تصویر برچسب"), FILE_CHOOSER_CODE);
                } catch (Exception e) {
                    filePathCallback = null;
                    callback.onReceiveValue(null);
                    return false;
                }
                return true;
            }
        });

        webView.loadUrl(START_URL);
    }

    /** Map https://appassets.local/<path> onto APK assets/. */
    private WebResourceResponse serveAsset(Uri url) {
        if (url == null || !HOST.equals(url.getHost())) {
            return null;
        }
        String path = url.getPath();
        if (path == null || path.isEmpty() || "/".equals(path)) {
            path = "/index.html";
        }
        String clean = path.substring(1);
        try {
            InputStream is = getAssets().open(clean);
            String mime = guessMime(clean);
            String enc = (mime.startsWith("text/") || mime.contains("javascript")
                    || mime.contains("json")) ? "utf-8" : null;
            Map<String, String> headers = new HashMap<String, String>();
            headers.put("Access-Control-Allow-Origin", "*");
            headers.put("Cache-Control", "no-cache");
            WebResourceResponse resp = new WebResourceResponse(mime, enc, is);
            resp.setResponseHeaders(headers);
            return resp;
        } catch (IOException e) {
            return null; // 404 -> WebView default handling
        }
    }

    private static String guessMime(String p) {
        String low = p.toLowerCase();
        if (low.endsWith(".html") || low.endsWith(".htm")) return "text/html";
        if (low.endsWith(".js")) return "text/javascript";
        if (low.endsWith(".css")) return "text/css";
        if (low.endsWith(".json")) return "application/json";
        if (low.endsWith(".webmanifest")) return "application/manifest+json";
        if (low.endsWith(".png")) return "image/png";
        if (low.endsWith(".jpg") || low.endsWith(".jpeg")) return "image/jpeg";
        if (low.endsWith(".svg")) return "image/svg+xml";
        if (low.endsWith(".ico")) return "image/x-icon";
        if (low.endsWith(".wasm")) return "application/wasm";
        if (low.endsWith(".gz")) return "application/gzip";
        if (low.endsWith(".ttf")) return "font/ttf";
        if (low.endsWith(".woff")) return "font/woff";
        if (low.endsWith(".woff2")) return "font/woff2";
        return "application/octet-stream";
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILE_CHOOSER_CODE && filePathCallback != null) {
            Uri[] result = null;
            if (data != null && data.getData() != null) {
                result = new Uri[]{data.getData()};
            }
            filePathCallback.onReceiveValue(result);
            filePathCallback = null;
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
