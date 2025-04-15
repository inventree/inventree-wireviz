import { apiUrl, checkPluginVersion, getDetailUrl, ModelType, type InvenTreePluginContext } from "@inventreedb/ui";
import { Button, Group, Stack, Text } from "@mantine/core";
import { IconTopologyStar } from "@tabler/icons-react";


function WirevizDashboard({ context }: { context: InvenTreePluginContext }) {

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
            <Text size='lg'>Upload Wireviz Diagram</Text>
            <Group gap='xs'>
                <IconTopologyStar />
                <Button onClick={() => newDiagram.open()}>Upload New Diagram</Button>
            </Group>
        </Stack>
        </>
    );
}


export function renderWirevizDashboard(context: InvenTreePluginContext) {
    checkPluginVersion(context);
    return (
        <WirevizDashboard context={context} />
    )
}