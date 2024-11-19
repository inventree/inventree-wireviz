import { Alert, MantineProvider, Stack, Text } from '@mantine/core';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';


function WirevizSettings({context}: {context: any}) {

    console.log("settings context:", context);

    return (
        <Stack gap="xs">
            <Alert color="green" title="Hello World">
                <Text>Check it out - custom settings code!!</Text>
            </Alert>
        </Stack>
    );
}


export function renderPluginSettings(target: HTMLElement | null, context: any) {

    createRoot(target!).render(
        <StrictMode>
            <MantineProvider>
                <WirevizSettings context={context} />
            </MantineProvider>
        </StrictMode>
    );
}

