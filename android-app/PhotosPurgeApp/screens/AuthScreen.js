import { NativeModules } from 'react-native';
import { useState } from 'react';
import { Button, View, Text, FlatList } from 'react-native';
import TransferButton from '../components/TransferButton';

const { PhotosAuthModule } = NativeModules; // ✅ Make sure this matches your native code!

export default function AuthScreen() {
  const [accounts, setAccounts] = useState([]);
  const [tokenInfo, setTokenInfo] = useState(null);

  const fetchAccounts = async () => {
    try {
      console.log('📢 [fetchAccounts] Button clicked');
      const accs = await PhotosAuthModule.listGoogleAccounts();
      console.log('✅ [fetchAccounts] Received accounts:', accs);
      setAccounts(accs);
    } catch (e) {
      console.error('❌ [fetchAccounts] Failed to list accounts:', e);
    }
  };

  const getTokenFor = async (accountName) => {
    try {
      console.log(`📢 [getTokenFor] Getting token for: ${accountName}`);
      const tokenData = await PhotosAuthModule.getToken(accountName);
      console.log('✅ [getTokenFor] Received token data:', tokenData);
      setTokenInfo(tokenData);
    } catch (e) {
      console.error('❌ [getTokenFor] Failed to get token:', e);
    }
  };

  return (
    <View style={{ padding: 20 }}>
      <Button title="List Google Accounts" onPress={fetchAccounts} />
      <FlatList
        data={accounts}
        keyExtractor={(item) => item.name}
        renderItem={({ item }) => (
          <Button title={item.name} onPress={() => getTokenFor(item.name)} />
        )}
      />

      {tokenInfo && (
        <View style={{ marginTop: 20 }}>
          <Text>Selected Account: {tokenInfo.accountName}</Text>
          <Text style={{ fontSize: 12 }}>Bearer Token: {tokenInfo.token}</Text>
          <TransferButton
            token={tokenInfo.token}
            email={tokenInfo.accountName}
          />
        </View>
      )}
    </View>
  );
}
