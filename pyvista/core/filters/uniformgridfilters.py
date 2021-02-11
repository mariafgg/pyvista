"""These classes hold methods to apply general filters to any data type.

By inheriting these classes into the wrapped VTK data structures, a user
can easily apply common filters in an intuitive manner.

Example
-------
>>> import pyvista
>>> from pyvista import examples
>>> dataset = examples.load_uniform()

>>> # Threshold
>>> thresh = dataset.threshold([100, 500])

>>> # Slice
>>> slc = dataset.slice()

>>> # Clip
>>> clp = dataset.clip(invert=True)

>>> # Contour
>>> iso = dataset.contour()

"""
import collections.abc

import vtk

from pyvista import DataSetFilters, UniformGrid
from pyvista.core.filters.algorithm import _update_alg, _get_output
from pyvista.utilities import (abstract_class)


@abstract_class
class UniformGridFilters(DataSetFilters):
    """An internal class to manage filters/algorithms for uniform grid datasets."""

    def gaussian_smooth(dataset, radius_factor=1.5, std_dev=2.,
                        scalars=None, preference='points', progress_bar=False):
        """Smooth the data with a Gaussian kernel.

        Parameters
        ----------
        radius_factor : float or iterable, optional
            Unitless factor to limit the extent of the kernel.

        std_dev : float or iterable, optional
            Standard deviation of the kernel in pixel units.

        scalars : str, optional
            Name of scalars to process. Defaults to currently active scalars.

        preference : str, optional
            When scalars is specified, this is the preferred array type to
            search for in the dataset.  Must be either ``'point'`` or ``'cell'``

        progress_bar : bool, optional
            Display a progress bar to indicate progress.
        """
        alg = vtk.vtkImageGaussianSmooth()
        alg.SetInputDataObject(dataset)
        if scalars is None:
            field, scalars = dataset.active_scalars_info
        else:
            _, field = dataset.get_array(scalars, preference=preference, info=True)
        alg.SetInputArrayToProcess(0, 0, 0, field.value, scalars) # args: (idx, port, connection, field, name)
        if isinstance(radius_factor, collections.abc.Iterable):
            alg.SetRadiusFactors(radius_factor)
        else:
            alg.SetRadiusFactors(radius_factor, radius_factor, radius_factor)
        if isinstance(std_dev, collections.abc.Iterable):
            alg.SetStandardDeviations(std_dev)
        else:
            alg.SetStandardDeviations(std_dev, std_dev, std_dev)
        _update_alg(alg, progress_bar, 'Performing Gaussian Smoothing')
        return _get_output(alg)

    def extract_subset(dataset, voi, rate=(1, 1, 1), boundary=False):
        """Select piece (e.g., volume of interest).

        To use this filter set the VOI ivar which are i-j-k min/max indices
        that specify a rectangular region in the data. (Note that these are
        0-offset.) You can also specify a sampling rate to subsample the
        data.

        Typical applications of this filter are to extract a slice from a
        volume for image processing, subsampling large volumes to reduce data
        size, or extracting regions of a volume with interesting data.

        Parameters
        ----------
        voi : tuple(int)
            Length 6 iterable of ints: ``(xmin, xmax, ymin, ymax, zmin, zmax)``.
            These bounds specify the volume of interest in i-j-k min/max
            indices.

        rate : tuple(int)
            Length 3 iterable of ints: ``(xrate, yrate, zrate)``.
            Default: ``(1, 1, 1)``

        boundary : bool
            Control whether to enforce that the "boundary" of the grid is
            output in the subsampling process. (This only has effect
            when the rate in any direction is not equal to 1). When
            this is on, the subsampling will always include the boundary of
            the grid even though the sample rate is not an even multiple of
            the grid dimensions. (By default this is off.)
        """
        alg = vtk.vtkExtractVOI()
        alg.SetVOI(voi)
        alg.SetInputDataObject(dataset)
        alg.SetSampleRate(rate)
        alg.SetIncludeBoundary(boundary)
        alg.Update()
        result = _get_output(alg)
        # Adjust for the confusing issue with the extents
        #   see https://gitlab.kitware.com/vtk/vtk/-/issues/17938
        fixed = UniformGrid()
        fixed.origin = result.bounds[::2]
        fixed.spacing = result.spacing
        fixed.dimensions = result.dimensions
        fixed.point_arrays.update(result.point_arrays)
        fixed.cell_arrays.update(result.cell_arrays)
        fixed.field_arrays.update(result.field_arrays)
        fixed.copy_meta_from(result)
        return fixed