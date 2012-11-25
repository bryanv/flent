## -*- coding: utf-8 -*-
##
## formatters.py
##
## Author:   Toke Høiland-Jørgensen (toke@toke.dk)
## Date:     16 oktober 2012
## Copyright (c) 2012, Toke Høiland-Jørgensen
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pprint, sys, csv



class Formatter(object):

    def __init__(self, output, config):
        self.config = config
        if isinstance(output, basestring):
            if output == "-":
                self.output = sys.stdout
            else:
                self.output = open(output, "w")
        else:
            self.output = output

    def format(self, name, results):
        self.output.write(name+"\n")
        self.output.write(results+"\n")



class OrgTableFormatter(Formatter):
    """Format the output for an Org mode table. The formatter is pretty crude
    and does not align the table properly, but it should be sufficient to create
    something that Org mode can correctly realign."""

    def format(self, name, results):

        if not results:
            self.output.write(unicode(name) + u" -- empty\n")
        keys = [i for i in self.config.sections() if i != 'global']
        header_row = [name] + keys
        self.output.write(u"| " + u" | ".join(header_row) + u" |\n")
        self.output.write(u"|-" + u"-+-".join([u"-"*len(i) for i in header_row]) + u"-|\n")

        def format_item(item):
            if isinstance(item, float):
                return "%.2f" % item
            return unicode(item)

        for row in results.zipped(keys):
            self.output.write(u"| ")
            self.output.write(u" | ".join(map(format_item, row)))
            self.output.write(u" |\n")


DefaultFormatter = OrgTableFormatter

class CsvFormatter(Formatter):
    """Format the output as csv."""

    def format(self, name, results):

        if not results:
            return

        writer = csv.writer(self.output)
        keys = [i for i in self.config.sections() if i != 'global']
        header_row = [name] + keys
        writer.writerow(header_row)

        def format_item(item):
            if item is None:
                return ""
            return unicode(item)

        for row in results.zipped(keys):
            writer.writerow(map(format_item, row))

class PlotFormatter(Formatter):

    def __init__(self, output, config):
        self.output = output
        self.config = config
        try:
            import matplotlib, numpy
            # If saving to file, try our best to set a proper backend for
            # matplotlib according to the output file name. This helps with
            # running matplotlib without an X server.
            if output != "-":
                if output.endswith('.svg') or output.endswith('.svgz'):
                    matplotlib.use('svg')
                elif output.endswith('.ps') or output.endswith('.eps'):
                    matplotlib.use('ps')
                elif output.endswith('.pdf'):
                    matplotlib.use('pdf')
                elif output.endswith('.png'):
                    matplotlib.use('agg')
                else:
                    raise RuntimeError("Unrecognised file format for output '%s'" % output)
            import matplotlib.pyplot as plt
            self.plt = plt
            self.np = numpy
            self._init_subplots()
        except ImportError:
            raise RuntimeError(u"Unable to plot -- matplotlib is missing! Please install it if you want plots.")


    def _init_subplots(self):
        series_names = [i for i in self.config.sections() if i != 'global']
        plots = sorted(set([self.config.getint(s, 'subplot', 1) for s in series_names]))
        num_plots = len(plots)
        if plots != range(1, num_plots+1):
            raise RuntimeError(u"Plots are not numbered sequentially")

        self.fig, self.axs = self.plt.subplots(num_plots, 2, sharex=True, sharey=False, squeeze=False)


        # Hide all axes (they are then shown when used below)
        for a in self.axs.flatten():
            a.yaxis.set_visible(False)

        for s in series_names:
            # Each series is plotted on the appropriate axis with the series
            # name as label. The line parameters are optionally set in the
            # config file; if no value is set, matplotlib selects default
            # colours for the lines.
            subfig = self.config.getint(s, 'subplot', 1)-1
            axis = self.config.getint(s, 'plot_axis', 1)-1
            a = self.axs[subfig,axis]
            a.yaxis.set_visible(True)

            limits = self.config.get(s, 'limits', None)
            if limits is not None:
                l_min,l_max = [float(i) for i in limits.split(",")]
                y_min,y_max = a.get_ylim()
                a.set_ylim(min(y_min,l_min), max(y_max,l_max))

            # Scales start out with a scale of 'linear', change it if a scale is set
            scale = self.config.get(s, 'scale', None)
            if scale is not None:
                a.set_yscale(scale)

            # Set plot axis labels to the unit of the series, if set. Detect
            # multiple incompatibly set units and abort if found.
            units = self.config.get(s, 'units', '')
            label = a.get_ylabel()
            if label == '':
                a.set_ylabel(units)
            elif units and label != units:
                raise RuntimeError(u"Axis units mismatch: %s and %s for subplot %d" % (units,label,subfig))


        self.axs[-1,0].set_xlabel(self.config.get('global', 'x_label', ''))
        xlimits = self.config.get('global', 'x_limits', None)
        if xlimits is not None:
            l_min,l_max = [float(i) for i in xlimits.split(",")]
            self.axs[0,0].set_xlim(l_min,l_max)


        self.fig.suptitle(self.config.get('global', 'plot_title', ''), fontsize=16)

        self.fig.subplots_adjust(left=0.1, right=0.9)

        # Duplicate the twinx() function of axes for having the second set of
        # axes be on top of the others, for dual-axis view
        for axs in self.axs:
            box = axs[0].get_position()
            axs[0].set_position([box.x0, box.y0, box.width * 2.0, box.height])
            axs[1].set_position(axs[0].get_position())
            axs[1].set_frame_on(False)
            axs[1].yaxis.tick_right()
            axs[1].yaxis.set_label_position('right')
            axs[1].yaxis.set_offset_position('right')
            axs[1].xaxis.set_visible(False)


    def format(self, name, results):
        if not results:
            return

        # Unzip the data into time series and data dicts to allow for plotting.
        t,data = zip(*results)
        series_names = [i for i in self.config.sections() if i != 'global']

        # The config file can set plot_axis to 1 or 2 for each test depending on
        # which axis the results should be plotted. The second axis is only
        # created if it is selected in one of the data sets selects it. The
        # matplotlib .twinx() function creates a second axis on the right-hand
        # side of the plot in the obvious way.

        all_data = self.np.empty_like(self.axs, dtype=object)
        for i in range(len(all_data.flat)):
            all_data.flat[i] = []

        for s in series_names:
            # Each series is plotted on the appropriate axis with the series
            # name as label. The line parameters are optionally set in the
            # config file; if no value is set, matplotlib selects default
            # colours for the lines.
            subfig = self.config.getint(s, 'subplot', 1)-1
            axis = self.config.getint(s, 'plot_axis', 1)-1
            a = self.axs[subfig,axis]

            # Set optional kwargs from config file
            kwargs = {}
            linewidth=self.config.get(s,'plot_linewidth', None)
            if linewidth is not None:
                kwargs['linewidth'] = float(linewidth)
            color=self.config.get(s, 'plot_linecolor', None)
            if color is not None:
                kwargs['color'] = color

            data_points = [d[s] for d in data]
            if self.config.has_option(s, 'limits'):
                all_data[subfig,axis] = None

            if all_data[subfig,axis] is not None:
                all_data[subfig,axis] += [d for d in data_points if d is not None]


            a.plot(t,
                   data_points,
                   self.config.get(s, 'plot_line', ''),
                   label=self.config.get(s, 'plot_label', s),
                   **kwargs
                )


        for n,axs in enumerate(self.axs):
            # Each axis has a set of handles/labels for the legend; combine them
            # into one list of handles/labels for displaying one legend that holds
            # all plot lines
            handles, labels = reduce(lambda x,y:(x[0]+y[0], x[1]+y[1]),
                                     [a.get_legend_handles_labels() for a in axs if a is not None])

            # Shrink the current subplot by 20% in the horizontal direction, and
            # place the legend on the right of the plot.
            for i in 0,1:
                box = axs[i].get_position()
                axs[i].set_position([box.x0, box.y0, box.width * 0.8, box.height])

                if self.config.getboolean('global', 'plot_outlier_scaling', True) \
                  and all_data[n,i]:
                    # If outlier scaling is turned off and no manual scaling for the
                    # axis is specified, find the 95th and 5th percentile of data
                    # points and scale the axis to these values (plus five percent
                    # air).

                    top_percentile = self.np.percentile(all_data[n,i], 95)*1.05
                    btm_percentile = self.np.percentile(all_data[n,i], 5)*0.95
                    axs[i].set_ylim(ymin=btm_percentile, ymax=top_percentile)

            axs[0].legend(handles, labels,
                          bbox_to_anchor=(1.05, 1.0),
                          loc='upper left', borderaxespad=0.,
                          title=self.config.get('global', 'legend%d_title'%(n+1), ''),
                          prop={'size':'small'})

        # Since outputting image data to stdout does not make sense, we launch
        # the interactive matplotlib viewer if stdout is set for output.
        # Otherwise, the filename is passed to matplotlib, which selects an
        # appropriate output format based on the file name.
        if self.output == "-":
            self.plt.show()
        else:
            self.plt.savefig(self.output)
