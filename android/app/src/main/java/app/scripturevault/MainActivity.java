package app.scripturevault;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.webkit.WebViewAssetLoader;

// Scripture Vault runs entirely on the phone: both Bibles and the app page are bundled inside; notes are saved on the device.
public class MainActivity extends Activity {
  private WebView web;

  @Override protected void onCreate(Bundle saved) {
    super.onCreate(saved);
    final WebViewAssetLoader loader = new WebViewAssetLoader.Builder()
        .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this)).build();
    web = new WebView(this);
    WebSettings s = web.getSettings();
    s.setJavaScriptEnabled(true);
    s.setDomStorageEnabled(true);
    s.setTextZoom(100);
    // Everything is bundled in the app, so never use a stale saved copy of the pages.
    s.setCacheMode(WebSettings.LOAD_NO_CACHE);
    web.clearCache(true);
    web.setWebViewClient(new WebViewClient() {
      @Override public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) { return loader.shouldInterceptRequest(r.getUrl()); }
    });
    setContentView(web);
    web.loadUrl("https://appassets.androidplatform.net/assets/index.html");
  }

  @Override public void onBackPressed() {
    web.evaluateJavascript("window.fvBack ? window.fvBack() : false", v -> {
      if (!"true".equals(v)) MainActivity.super.onBackPressed();
    });
  }
}
