import { InvenTreePluginContext } from '@inventreedb/ui';
import { Alert, Stack, Text } from '@mantine/core';



function WirevizSettings({context}: {context: InvenTreePluginContext}) {

    console.log("settings context:", context);

    return (
        <Stack gap="xs">
            <Alert color="green" title="Hello World">
                <Text>Check it out - custom settings code!!</Text>
            </Alert>
        </Stack>
    );
}


export function renderPluginSettings(context: InvenTreePluginContext) {

    return (
        <WirevizSettings context={context} />
    );
}

