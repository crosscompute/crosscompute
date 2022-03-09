from ..constants import (
    MUTATION_ROUTE)


class MutationRoutes():

    def __init__(self, infos_by_timestamp):
        self._infos_by_timestamp = infos_by_timestamp

    def includeme(self, config):
        config.add_route('mutation', MUTATION_ROUTE.format(uri='{uri:.*}'))

        config.add_view(
            self.see_mutation,
            route_name='mutation',
            renderer='json')

    def see_mutation(self, request):
        print(request.params)
        print(request.matchdict)
        print(self._infos_by_timestamp)
        '''
        params = request.params
        old_timestamp = float(params.get('timestamp', 0))
        new_timestamp = time()
        folder = self.get_folder_from(request)
        packs = []
        for t, ps in change_packs_by_timestamp.items():
            if t > old_timestamp:
                packs.extend(ps)
        for file_code, file_path in packs:
            # lookup definition for file path
            # check whether this file path is relevant to this uri
            template is associated with an automation definition and mode
            variable is associated with an automation definition,
            batch_definition and mode
            # if the file path does not start with folder, ignore
            if is configuration, style, template, trigger refresh
            if is variable
                get variable definition
                get variable id
                render the variable
        # return variables or trigger refresh if necessary
        return {
            'configurations': configurations,
            'styles': styles,
            'templates': templates,
            'variables': variables,
            'mutation_timestamp': new_timestamp,
        }
        '''
        return {}
