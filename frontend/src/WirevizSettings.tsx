import { apiUrl, getDetailUrl, ModelType, type InvenTreePluginContext } from '@inventreedb/ui';
import { Alert, Button, Group, Stack, Table, Text, Title, Tooltip } from '@mantine/core';
import { IconCirclePlus, IconTrash } from '@tabler/icons-react';
import { useMemo, useState } from 'react';



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

    const newTemplate = context.forms.create({
        title: "Upload New Template",
        url: apiUrl("/plugin/wireviz/upload-template/"),
        fields: {
            template: {}
        },
        successMessage: 'Template uploaded',
        onFormSuccess: () => {
            // TODO: Refresh table?
        }
    });

    const [ selectedTemplate, setSelectedTemplate ] = useState<string | null>(null);
    
    const deleteTemplate = context.forms.create({
        title: "Delete Template",
        url: apiUrl("/plugin/wireviz/delete-template/"),
        fields: {
            template: {
                value: selectedTemplate,
                hidden: true,
            }
        },
        preFormContent: (
            <Alert color='orange' title='Delete Template'>
                <Text>Are you sure you want to delete this template?</Text>
                <Text>This action cannot be undone!</Text>
            </Alert>
        ),
        submitColor: 'red',
        submitText: 'Delete',
        successMessage: 'Template deleted',
        onFormSuccess: () => {
            // TODO: Refresh table?
        }
    });

    const templates : string[] = useMemo(() => context.context?.templates ?? [], [context.context]);

    return (
        <>
        {newDiagram.modal}
        {newTemplate.modal}
        {deleteTemplate.modal}
        <Stack gap='xs'>
            <Group gap='xs'>
                <Tooltip label="Upload new diagram">
                    <Button onClick={() => newDiagram.open()}>Upload New Diagram</Button>
                </Tooltip>
            </Group>
            <Group justify='space-between'>
                <Title order={4}>Templates</Title>
                <Tooltip label="Upload new template">
                <Button variant='outline' color='green' onClick={newTemplate.open}>
                    <IconCirclePlus />
                </Button>
                </Tooltip>
            </Group>
            {templates.length > 0 ? (
                <Table striped>
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Td>Template File</Table.Td>
                            <Table.Td />
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        {templates.map((template) => (
                            <Table.Tr key={template}>
                                <Table.Td>
                                    <Text>{template}</Text>
                                </Table.Td>
                                <Table.Td>
                                    <Group justify='right'>
                                        <Tooltip label="Delete template">
                                        <Button
                                            variant='outline'
                                            color='red'
                                            onClick={() => {
                                                setSelectedTemplate(template);
                                                deleteTemplate.open();
                                            }}
                                            >
                                            <IconTrash />
                                        </Button>
                                        </Tooltip>
                                    </Group>
                                </Table.Td>
                            </Table.Tr>
                        ))}
                    </Table.Tbody>
                </Table>
            ) : (
                <Alert color='blue' title='No templates found'>
                    <Text>Upload a template to get started!</Text>
                </Alert>
            )}
        </Stack>
        </>
    );
}


export function renderPluginSettings(context: InvenTreePluginContext) {

    return (
        <WirevizSettings context={context} />
    );
}

