package com.photospurgeapp

import android.accounts.AccountManager
import android.app.Activity
import android.content.Intent
import com.facebook.react.bridge.*

class PhotosAuthModule(reactContext: ReactApplicationContext) : ReactContextBaseJavaModule(reactContext) {
  override fun getName(): String = "PhotosAuthModule"

  @ReactMethod
  fun getAccounts(promise: Promise) {
    val am = AccountManager.get(reactApplicationContext)
    val accounts = am.getAccountsByType("com.google").map { it.name }
    promise.resolve(Arguments.fromList(accounts))
  }

  @ReactMethod
  fun getToken(email: String, promise: Promise) {
    val am = AccountManager.get(reactApplicationContext)
    val accounts = am.getAccountsByType("com.google")
    val account = accounts.find { it.name == email }
    if (account == null) {
      promise.reject("404", "Account not found")
      return
    }
    am.getAuthToken(account, "oauth2:https://www.googleapis.com/auth/photoslibrary.readonly", null, false, {
      val result = it.result
      val token = result.getString(AccountManager.KEY_AUTHTOKEN)
      promise.resolve(token)
    }, null)
  }
}

