# Fish completion for mdfs

complete -c mdfs -n '__fish_use_subcommands' -a 'init' -d 'Initialize .mdfs directory'
complete -c mdfs -n '__fish_use_subcommands' -a 'bundle' -d 'Bundle rules and/or files into a context Markdown file'
complete -c mdfs -n '__fish_use_subcommands' -a 'paste' -d 'Save clipboard as response, optionally extract files'
complete -c mdfs -n '__fish_use_subcommands' -a 'extract' -d 'Extract files and apply patches from Markdown'
complete -c mdfs -n '__fish_use_subcommands' -a 'log' -d 'Show chronological log of contexts and responses'
complete -c mdfs -n '__fish_use_subcommands' -a 'setup' -d 'Install/uninstall shell completions'

# Global options
complete -c mdfs -s d -l dir -r -d 'Project directory'
complete -c mdfs -l contexts-dir -r -d 'Override contexts directory (overrides .mdfsrc.yaml)'
complete -c mdfs -l responses-dir -r -d 'Override responses directory (overrides .mdfsrc.yaml)'
complete -c mdfs -l rules-dir -r -d 'Override rules directory (overrides .mdfsrc.yaml)'
complete -c mdfs -s v -l version -d 'Show version'

# init
complete -c mdfs -n '__fish_seen_subcommand_from init' -s d -l dir -r -d 'Project directory'
complete -c mdfs -n '__fish_seen_subcommand_from init' -l contexts-dir -r -d 'Override contexts directory'
complete -c mdfs -n '__fish_seen_subcommand_from init' -l responses-dir -r -d 'Override responses directory'
complete -c mdfs -n '__fish_seen_subcommand_from init' -l rules-dir -r -d 'Override rules directory'

# bundle
complete -c mdfs -n '__fish_seen_subcommand_from bundle' -s d -l dir -r -d 'Project directory'
complete -c mdfs -n '__fish_seen_subcommand_from bundle' -s l -l label -r -d 'Label for the context file'
complete -c mdfs -n '__fish_seen_subcommand_from bundle' -s o -l output -r -d 'Custom output path'
complete -c mdfs -n '__fish_seen_subcommand_from bundle' -s q -l query -r -d 'User question to append to the bundle'
complete -c mdfs -n '__fish_seen_subcommand_from bundle' -l clip -d 'Also copy the bundle to clipboard'
complete -c mdfs -n '__fish_seen_subcommand_from bundle' -l rules -r -d 'Additional rules to include, by filename globs'
complete -c mdfs -n '__fish_seen_subcommand_from bundle' -l no-preamble -d 'Disable preamble and table of contents'
complete -c mdfs -n '__fish_seen_subcommand_from bundle' -l no-gitignore -d 'Include files that are in .gitignore'
complete -c mdfs -n '__fish_seen_subcommand_from bundle' -l contexts-dir -r -d 'Override contexts directory'
complete -c mdfs -n '__fish_seen_subcommand_from bundle' -l responses-dir -r -d 'Override responses directory'
complete -c mdfs -n '__fish_seen_subcommand_from bundle' -l rules-dir -r -d 'Override rules directory'

# paste
complete -c mdfs -n '__fish_seen_subcommand_from paste' -s d -l dir -r -d 'Project directory'
complete -c mdfs -n '__fish_seen_subcommand_from paste' -s x -l extract -d 'Also extract files and apply patches'
complete -c mdfs -n '__fish_seen_subcommand_from paste' -l dry-run -d 'Show what would happen without writing'
complete -c mdfs -n '__fish_seen_subcommand_from paste' -l contexts-dir -r -d 'Override contexts directory'
complete -c mdfs -n '__fish_seen_subcommand_from paste' -l responses-dir -r -d 'Override responses directory'
complete -c mdfs -n '__fish_seen_subcommand_from paste' -l rules-dir -r -d 'Override rules directory'

# extract
complete -c mdfs -n '__fish_seen_subcommand_from extract' -s d -l dir -r -d 'Project directory'
complete -c mdfs -n '__fish_seen_subcommand_from extract' -s f -l force -d 'Force overwrite all existing files'
complete -c mdfs -n '__fish_seen_subcommand_from extract' -l dry-run -d 'Show actions without writing'
complete -c mdfs -n '__fish_seen_subcommand_from extract' -l contexts-dir -r -d 'Override contexts directory'
complete -c mdfs -n '__fish_seen_subcommand_from extract' -l responses-dir -r -d 'Override responses directory'
complete -c mdfs -n '__fish_seen_subcommand_from extract' -l rules-dir -r -d 'Override rules directory'

# log
complete -c mdfs -n '__fish_seen_subcommand_from log' -s d -l dir -r -d 'Project directory'
complete -c mdfs -n '__fish_seen_subcommand_from log' -l contexts-dir -r -d 'Override contexts directory'
complete -c mdfs -n '__fish_seen_subcommand_from log' -l responses-dir -r -d 'Override responses directory'
complete -c mdfs -n '__fish_seen_subcommand_from log' -l rules-dir -r -d 'Override rules directory'

# setup
complete -c mdfs -n '__fish_seen_subcommand_from setup' -s i -l install-completions -d 'Install shell completions for current shell'
complete -c mdfs -n '__fish_seen_subcommand_from setup' -s u -l uninstall-completions -d 'Uninstall shell completions'
