import React, { useState } from 'react';
import { View, Text, TextInput, Button } from 'react-native';

export default function AccountSelectScreen({ navigation, route }) {
  const [destinationEmail, setDestinationEmail] = useState('');
  const { cookies } = route.params;

  return (
    <View style={{ padding: 20 }}>
      <Text>Enter Destination Google Email:</Text>
      <TextInput
        placeholder="example@gmail.com"
        style={{ borderBottomWidth: 1, marginBottom: 20 }}
        value={destinationEmail}
        onChangeText={setDestinationEmail}
      />
      <Button
        title="Start Migration"
        onPress={() =>
          navigation.navigate('Migrate', { cookies, destinationEmail })
        }
      />
    </View>
  );
}

