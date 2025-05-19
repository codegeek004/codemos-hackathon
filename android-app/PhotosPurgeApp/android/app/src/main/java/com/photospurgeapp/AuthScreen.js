import { NativeModules } from 'react-native';
import { useState } from 'react';
import { Button, View, Text, FlatList } from 'react-native';

const { PhotosAuth } = NativeModules;

export default function AuthScreen() {
  const [accounts, setAccounts] = useState([]);
  const [tokenInfo, setTokenInfo] = useState(null);

  const fetchAccounts = async () => {
    const accs = await PhotosAuth.listGoogleAccounts();
    setAccounts(accs);
  };

  const getTokenFor = async (accountName) => {
    const tokenData = await PhotosAuth.getToken(accountName);
    setTokenInfo(tokenData);
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
        </View>
      )}
    </View>
  );
}

