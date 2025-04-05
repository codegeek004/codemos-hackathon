import React, { useEffect, useState } from 'react';
import { View, Text, Button, ScrollView } from 'react-native';
import axios from 'axios';

const FetchPhotosScreen = ({ route }) => {
    const { cookies } = route.params;
    const [photoUrls, setPhotoUrls] = useState([]);

    const fetchPhotoDirectUrl = async (photoId) => {
        const batchUrl = "https://photos.google.com/_/PhotosUi/data/batchexecute";
        const payload = `f.req=[[["wQ6iqd","[[\\"${photoId}\\"]]",null,"generic"]]]`;

        try {
            let response = await axios.post(batchUrl, payload, {
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "Cookie": Object.entries(cookies).map(([key, value]) => `${key}=${value.value}`).join('; ')
                }
            });

            console.log("Google Photos Response:", response.data);
            // Extract the direct photo URL from response (parsing needed)
            const photoUrl = extractPhotoUrl(response.data);
            setPhotoUrls((prevUrls) => [...prevUrls, photoUrl]);
        } catch (error) {
            console.error("Request failed:", error);
        }
    };

    return (
        <ScrollView>
            <View style={{ padding: 20 }}>
                <Text style={{ fontSize: 18, fontWeight: 'bold' }}>Fetched Photos</Text>
                {photoUrls.length > 0 ? (
                    photoUrls.map((url, index) => (
                        <Text key={index}>{url}</Text>
                    ))
                ) : (
                    <Text>No photos fetched yet.</Text>
                )}
                <Button title="Fetch Photos" onPress={() => fetchPhotoDirectUrl("AF1QipOmPg4YtOGwDHginSXGG2T4gDB-AOBqhQ3azE3w")} />
            </View>
        </ScrollView>
    );
};

// Helper function to parse response and extract photo URL
const extractPhotoUrl = (responseData) => {
    try {
        //let match = responseData.match(/"https:\\/\\/lh3.googleusercontent.com\\/(.*?)"/);
        let match = responseData.match(/"https:\/\/lh3\.googleusercontent\.com\/(.*?)"/);

        if (match) {
            return `https://lh3.googleusercontent.com/${match[1]}`;
        }
    } catch (error) {
        console.error("Error parsing photo URL:", error);
    }
    return null;
};

export default FetchPhotosScreen;

