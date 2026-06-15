import { apiUrl, getDetailUrl, ModelType, type InvenTreePluginContext } from '@inventreedb/ui';
import { Button, Group, Stack, Tooltip } from '@mantine/core';


function WirevizSettings({context}: {context: InvenTreePluginContext}) {

    const newDiagram = context.forms.create({
        title: 'Upload New Wireviz Diagram',
        url: apiUrl("/plugin/wireviz/upload/"),
        method: 'POST',
        fields: {
            part: {
                filters: {
                    active: true,
                    assembly: true,
                }
            },
            file: {},
        },
        successMessage: 'Wireviz diagram uploaded',
        onFormSuccess: (data: any) => {
            // Navigate to the selected part
            if (data?.part) {
                const url = getDetailUrl(ModelType.part, data.part);
                context.navigate(`${url}/wireviz`);
            }
        }
    });

    return (
        <>
        {newDiagram.modal}
        <Stack gap='xs'>
            <Group gap='xs'>
                <Tooltip label="Upload new diagram">
                    <Button onClick={() => newDiagram.open()}>Upload New Diagram</Button>
                </Tooltip>
            </Group>
        </Stack>
        </>
    );
}


export function renderPluginSettings(context: InvenTreePluginContext) {

    return (
        <WirevizSettings context={context} />
    );
}

