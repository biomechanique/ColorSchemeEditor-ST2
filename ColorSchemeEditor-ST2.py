import sublime, sublime_plugin, os

# globals suck, but don't know how to pass data between the classes
_schemeEditor = None
_skipOne = 0
_wasSingleLayout = None

def find_best_match ( scope, founds ):
	global _schemeEditor

	ret = None
	maxscore = 0

	# find the scope in the xml that matches the most
	for found in founds:
		foundstr = _schemeEditor.substr( found )
		pos = foundstr.find( '<string>' ) + 8
		foundstr = foundstr[ pos : -9 ]
		foundstrs = foundstr.split( ',' )
		fstrlen = 0
		for fstr in foundstrs:
			pos += fstrlen
			fstrlen = len( fstr )
			fstr = fstr.lstrip( ' ' )
			padleft = fstrlen - len( fstr )
			pos += padleft
			fstr = fstr.rstrip( ' ' )
			fstrlen += 1
			score = sublime.score_selector( scope, fstr )
			if maxscore == 0 or score > maxscore:
				maxscore = score
				ret = [ found, pos, pos + len( fstr ) ]

	if ret == None:
		return ret
	else:
		a = ret[0].a
		return sublime.Region( a + ret[1], a + ret[2] )


def update_view_status ( view ):
	found = None;
	
	# find the scope under the cursor
	scope_name = view.scope_name( view.sel()[0].a ).strip( ' ' ).replace( ' ', ' > ' )
	sublime.status_message( 'Syntax scope: ' + scope_name )
	scopes = reversed( scope_name.split( ' > ' ) )
	
	# convert to regex and look for the scope in the scheme editor
	for scope in scopes:
		if len( scope ) == 0:
			continue
		dots = scope.count( '.' )
		regex = '<key>scope</key>\\s*<string>([a-z\.]* ?, ?)*('
		regex += scope.replace( '.', '(\\.' )
		while dots > 0:
			regex += ')?'
			dots -= 1
		regex += ')( ?, ?[a-z\.]*)*</string>'
		
		found = _schemeEditor.find_all( regex, 0 )
		found = find_best_match( scope, found )
		if found != None:
			break

	_schemeEditor.sel().clear()
	if found == None:
		_schemeEditor.sel().add( sublime.Region( 0, 0 ) )
		_schemeEditor.show( 0 )
	else:
		_schemeEditor.sel().add( found )
		_schemeEditor.show_at_center( found )


def kill_scheme_editor ():
	global _schemeEditor, _skipOne, _wasSingleLayout
	# this crashes ST2 if placed here
	# if _wasSingleLayout != None:
	# 	_wasSingleLayout.set_layout( {
	# 		'cols': [0.0, 1.0],
	# 		'rows': [0.0, 1.0],
	# 		'cells': [[0, 0, 1, 1]]
	# 	} )
	_skipOne = 0
	_wasSingleLayout = None
	_schemeEditor = None


# listeners to update our scheme editor
class NavigationHistoryRecorder ( sublime_plugin.EventListener ):

	def on_close ( self, view ):
		global _schemeEditor
		if _schemeEditor != None:
			if _schemeEditor.id() == view.id():
				kill_scheme_editor()

	def on_selection_modified ( self, view ):
		global _schemeEditor, _skipOne
		if _schemeEditor != None:
			if _schemeEditor.id() != view.id():
				# for some reason this callback is called twice - for mouse down and mouse up
				if _skipOne == 1:
					_skipOne = 0
				else:
					_skipOne = 1
					update_view_status( view )


class EditCurrentColorSchemeCommand ( sublime_plugin.TextCommand ):
	'''Edit current color scheme
	'''
	
	def run( self, edit ):
		global _schemeEditor, _wasSingleLayout
		
		view = self.view
		viewid = view.id()
		window = view.window()
		if _schemeEditor == None:

			# see if not trying to edit on the scheme file
			path = os.path.abspath( sublime.packages_path() + '/../' + view.settings().get( 'color_scheme' ) )
			if path == view.file_name():
				sublime.status_message( 'Select different file from the scheme you want to edit' )
				_schemeEditor = None
				return

			# see if we openeded a new view
			views = len( window.views() )
			_schemeEditor = window.open_file( path )
			if _schemeEditor == None:
				sublime.status_message( 'Could not open the scheme file' )
				return
			if views == len( window.views() ):
				views = 0
			else:
				views = 1

			# if we have only one splitter, open new one
			groups = window.num_groups()
			group = -1
			index = 0
			if groups == 1:
				_wasSingleLayout = window
				group = 1
				window.set_layout( {
					'cols': [0.0, 0.5, 1.0],
					'rows': [0.0, 1.0],
					'cells': [[0, 0, 1, 1], [1, 0, 2, 1]]
				} )
			elif views == 1:
				activegrp = window.active_group() + 1
				if activegrp == groups:
					group = activegrp - 2
					index = len( window.views_in_group( group ) )
				else:
					group = activegrp

			if groups == 1 or views == 1:
				# move the editor to another splitter
				window.set_view_index( _schemeEditor, group, index )
			else:
				#if the editor is in different splitter already focus it
				window.focus_view( _schemeEditor )
			
			window.focus_view( view )
			update_view_status( view )

		else:
			# if it was us who created the other splitter close it
			if _wasSingleLayout != None:
				_wasSingleLayout.set_layout( {
					'cols': [0.0, 1.0],
					'rows': [0.0, 1.0],
					'cells': [[0, 0, 1, 1]]
				} )
			kill_scheme_editor()
			

		
		